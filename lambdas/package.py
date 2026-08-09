"""Build the per-state Lambda zips and deploy them to LocalStack.

Each zip contains:

- handler.py      the state's handler (imported as ``handler.handler``)
- common.py       shared S3 helpers
- reconcile.py    a copy of core/reconcile.py, so the exact same business
                  logic runs inside the Lambda containers as in the Django worker

Run from the project root:

    .venv/bin/python lambdas/package.py
"""

import os
import shutil
import tempfile
import zipfile

import boto3

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.join(ROOT, "lambdas")
ZIPS_DIR = os.path.join(HERE, ".zips")

LAMBDA_STATES = [
    ("ReconcileParseFile", "parse_file"),
    ("ReconcileMatchTransactions", "match_transactions"),
    ("ReconcileFlagMismatches", "flag_mismatches"),
    ("ReconcileComplete", "complete"),
]

STATE_MACHINE_NAME = "ReconciliationWorkflow"

ENDPOINT = "http://localhost:4566"
AWS_ACCESS_KEY_ID = "test"
AWS_SECRET_ACCESS_KEY = "test"


def build_zip(function_name, handler_module):
    os.makedirs(ZIPS_DIR, exist_ok=True)
    zip_path = os.path.join(ZIPS_DIR, f"{function_name}.zip")
    with tempfile.TemporaryDirectory() as tmp:
        shutil.copy(os.path.join(HERE, "handlers", f"{handler_module}.py"), os.path.join(tmp, "handler.py"))
        shutil.copy(os.path.join(HERE, "common.py"), os.path.join(tmp, "common.py"))
        shutil.copy(os.path.join(ROOT, "core", "reconcile.py"), os.path.join(tmp, "reconcile.py"))
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for fname in ("handler.py", "common.py", "reconcile.py"):
                zf.write(os.path.join(tmp, fname), arcname=fname)
    return zip_path


def upsert_function(client, name, zip_path):
    with open(zip_path, "rb") as f:
        code = f.read()
    kwargs = dict(
        FunctionName=name,
        Runtime="python3.11",
        Handler="handler.handler",
        Role="arn:aws:iam::000000000000:role/lambda-role",
        Code={"ZipFile": code},
        Environment={
            "Variables": {
                "LOCALSTACK_ENDPOINT": "http://localhost.localstack.cloud:4566",
                "S3_BUCKET": "reconciliation-uploads",
            }
        },
        Timeout=60,
    )
    try:
        client.create_function(**kwargs)
        print(f"created {name}")
    except client.exceptions.ResourceConflictException:
        client.update_function_code(FunctionName=name, ZipFile=code)
        print(f"updated {name}")
    return f"arn:aws:lambda:us-east-1:000000000000:function:{name}"


def deploy_state_machine(client, function_arns):
    with open(os.path.join(ROOT, "state_machine.json")) as f:
        definition = f.read()
    for name, arn in function_arns.items():
        definition = definition.replace(f"arn:aws:lambda:us-east-1:000000000000:function:{name}", arn)
    try:
        result = client.create_state_machine(
            name=STATE_MACHINE_NAME,
            definition=definition,
            roleArn="arn:aws:iam::000000000000:role/dummy-role",
        )
        print(f"created state machine {result['stateMachineArn']}")
        return result["stateMachineArn"]
    except client.exceptions.StateMachineAlreadyExists:
        result = client.update_state_machine(
            stateMachineArn=f"arn:aws:states:us-east-1:000000000000:stateMachine:{STATE_MACHINE_NAME}",
            definition=definition,
            roleArn="arn:aws:iam::000000000000:role/dummy-role",
        )
        print(f"updated state machine {result['updateDate']}")
        return f"arn:aws:states:us-east-1:000000000000:stateMachine:{STATE_MACHINE_NAME}"


def main():
    common = dict(
        endpoint_url=ENDPOINT,
        region_name="us-east-1",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    )
    lambda_client = boto3.client("lambda", **common)
    sfn_client = boto3.client("stepfunctions", **common)

    function_arns = {}
    for name, module in LAMBDA_STATES:
        zip_path = build_zip(name, module)
        function_arns[name] = upsert_function(lambda_client, name, zip_path)

    state_machine_arn = deploy_state_machine(sfn_client, function_arns)
    print(f"state machine arn: {state_machine_arn}")


if __name__ == "__main__":
    main()
