import json
import uuid
import boto3
import logging
import posixpath
from typing import Dict, Any
from datetime import datetime
from botocore.exceptions import ClientError, BotoCoreError, ParamValidationError

# ============================================================
# CONSTANTES DE CONFIG  (preencha aqui; nada via env vars)
# ============================================================
AGENT_REGION   = "us-east-1"              # região onde o Agent está publicado
AGENT_ID       = "QAYKR34TMW"  # ex.: "A1BCDEFGHIJKLMN"
AGENT_ALIAS_ID = "TSTALIASID"  # ex.: "TSTALIASID"
OUTPUT_BUCKET  = "alertas-caseiro"         # bucket de saída p/ salvar o alerta
SENDER_ID = "CAISEIRO"  # Replace with your actual Sender ID
DESTINATION_NUMBER = "+351..."  # Replace with your destination number (E.164 format)

# ============================================================
# LOGGING
# ============================================================
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# ============================================================
# CLIENTES AWS (apenas S3 aqui; o do Agent é criado com região no helper)
# ============================================================
s3 = boto3.client("s3")
sns_client = boto3.client('sns')

# ============================================================
# HELPERS
# ============================================================
def _basename_no_ext(key: str) -> str:
    base = posixpath.basename(key)
    dot = base.rfind(".")
    return base[:dot] if dot > 0 else base

def invoke_agent(input_text: str, session_id: str) -> str:
    """
    Invoca o Agent do Amazon Bedrock na região definida em AGENT_REGION.
    Retorna a resposta final (string concatenada do stream).
    """
    if not AGENT_ID or "REPLACE_WITH" in AGENT_ID:
        raise RuntimeError("AGENT_ID não configurado. Preencha AGENT_ID no topo do script.")
    if not AGENT_ALIAS_ID or "REPLACE_WITH" in AGENT_ALIAS_ID:
        raise RuntimeError("AGENT_ALIAS_ID não configurado. Preencha AGENT_ALIAS_ID no topo do script.")

    agent_rt = boto3.client("bedrock-agent-runtime", region_name=AGENT_REGION)

    resp = agent_rt.invoke_agent(
        agentId=AGENT_ID,
        agentAliasId=AGENT_ALIAS_ID,
        sessionId=session_id,
        inputText=input_text,
        endSession=False,
        enableTrace=False,
        sessionState={}
    )

    chunks = []
    for event in resp.get("completion", []):
        if "chunk" in event:
            chunks.append(event["chunk"]["bytes"].decode("utf-8"))
        elif "trace" in event:
            # Se quiser depurar, mude enableTrace=True e logue aqui
            pass

    return "".join(chunks).strip()

# ============================================================
# LAMBDA HANDLER
# ============================================================
def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Evento esperado:
    {
        "Records": [
            {
                "eventVersion": "2.1",
                "eventSource": "aws:s3",
                "awsRegion": "us-east-1",
                "eventTime": "2025-09-20T21:28:38.034Z",
                "eventName": "ObjectCreated:Put",
                "userIdentity": {
                    "principalId": "AWS:AROA3LZFPH2H2XCNOH5ZK:Participant"
                },
                "requestParameters": {
                    "sourceIPAddress": "94.62.170.149"
                },
                "responseElements": {
                    "x-amz-request-id": "QAXFVVKKVW1G5SV9",
                    "x-amz-id-2": "WQmz72FZEVkvENyDckpuA1vhO9LsNC7akjVUnC9YUYytGs/C7IV9sOA9LH47peVc7tpvvMUIem/G3+R9SJrf8WV3XNnQ9e1h2JISOciXBHs="
                },
                "s3": {
                    "s3SchemaVersion": "1.0",
                    "configurationId": "26265a80-2076-4ce3-82cd-d205850a56b0",
                    "bucket": {
                        "name": "aviario-metrics",
                        "ownerIdentity": {
                            "principalId": "A3CJJ5BGAZ3C2T"
                        },
                        "arn": "arn:aws:s3:::aviario-metrics"
                    },
                    "object": {
                        "key": "file_1.txt",
                        "size": 36,
                        "eTag": "96af14246b2154b0cfc82529b338b444",
                        "sequencer": "0068CF1C86053AA343"
                    }
                }
            }
        ]
    }
    """

    try:
        logger.info(event)

        # 1) Parâmetros mínimos do evento
        bucket = event["Records"][0]["s3"]["bucket"]["name"]
        key = event["Records"][0]["s3"]["object"]["key"]

        # 2) Ler arquivo de entrada do S3
        logger.info(f"Lendo s3://{bucket}/{key}")
        s3_obj = s3.get_object(Bucket=bucket, Key=key)
        file_content = s3_obj["Body"].read().decode("utf-8")

        # 3) Montar prompt
        prompt = file_content

        # 4) Invocar Agent
        session_id = str(uuid.uuid4())
        logger.info(f"Invocando Agent {AGENT_ID}/{AGENT_ALIAS_ID} na região {AGENT_REGION} (session={session_id})")
        answer = invoke_agent(prompt, session_id)  # string final

        logger.info(f"AI Agent answer: {answer}")

        # 5) Salvar saída no S3 (alerts/{basename}.json)
        out_key = f"alerts/{_basename_no_ext(key)}.json"
        payload = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "agent": {
                "agentId": AGENT_ID,
                "agentAliasId": AGENT_ALIAS_ID,
                "region": AGENT_REGION,
                "sessionId": session_id
            },
            "source": {"bucket": bucket, "key": key},
            "alert": answer
        }

        logger.info(f"Gravando s3://{OUTPUT_BUCKET}/{out_key}")
        s3.put_object(
            Bucket=OUTPUT_BUCKET,
            Key=out_key,
            Body=json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"),
            ContentType="application/json; charset=utf-8"
        )


        logger.info(f"A enviar SMS...")
        sms_response = send_sms(payload["alert"], DESTINATION_NUMBER, SENDER_ID)
        
        logger.info(f"SMS sent successfully. MessageId: {sms_response.get('MessageId')}")

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Success",
                "output_s3": f"s3://{OUTPUT_BUCKET}/{out_key}",
                "preview": answer[:300],
            }, ensure_ascii=False)
        }

    except KeyError as e:
        msg = f"Missing required parameter: {str(e)}"
        logger.error(msg)
        return {"statusCode": 400, "body": json.dumps({"error": "Bad Request", "message": msg})}

    except Exception as e:
        logger.exception("Erro inesperado")
        return {"statusCode": 500, "body": json.dumps({"error": "Internal Server Error", "message": str(e)})}

def send_sms(message: str, phone_number: str, sender_id: str) -> Dict[str, Any]:
    """
    Send SMS using Amazon SNS.
    
    Args:
        message: The SMS message content
        phone_number: Destination phone number in E.164 format
        sender_id: Sender ID for the SMS
        
    Returns:
        SNS publish response
        
    Raises:
        ClientError: If SNS operation fails
    """
    
    try:
        # Set SMS attributes
        message_attributes = {
            'AWS.SNS.SMS.SenderID': {
                'DataType': 'String',
                'StringValue': sender_id
            },
            'AWS.SNS.SMS.SMSType': {
                'DataType': 'String',
                'StringValue': 'Transactional'  # Use 'Promotional' for marketing messages
            }
        }
        
        # Send the SMS
        response = sns_client.publish(
            PhoneNumber=phone_number,
            Message=message,
            MessageAttributes=message_attributes
        )
        
        return response
        
    except ClientError as e:
        logger.error(f"Failed to send SMS: {e}")
        raise
