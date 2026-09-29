import requests
import json
import uuid

DUCK_AI_BASE_URL = "https://duck.ai"
TOKEN_ENDPOINT = f"{DUCK_AI_BASE_URL}/duckchat/v1/auth/token"
CHAT_ENDPOINT = f"{DUCK_AI_BASE_URL}/duckchat/v1/chat"

COMMON_HEADERS = {
    "Host": "duck.ai",
    "sec-ch-ua-platform": "\"Windows\"",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36",
    "sec-ch-ua": "\"Not=A?Brand\";v=\"99\", \"Brave\";v=\"151\", \"Chromium\";v=\"151\"",
    "dnt": "1",
    "sec-ch-ua-mobile": "?0",
    "accept": "*/*",
    "sec-gpc": "1",
    "accept-language": "en-US,en;q=0.5",
    "sec-fetch-site": "same-origin",
    "sec-fetch-mode": "cors",
    "sec-fetch-dest": "empty",
    "referer": "https://duck.ai/",
    "priority": "u=1, i"
}

# Tokens that we will capture or hardcode
VQD_4_TOKEN = ""

def get_vqd_token():
    global VQD_4_TOKEN
    headers = {
        **COMMON_HEADERS,
        "x-ddg-journey-id": "b55ec6c3834a487a0714ebb52db5ef83",
    }
    try:
        response = requests.get(TOKEN_ENDPOINT, headers=headers)
        response.raise_for_status()
        
        vqd_token = response.headers.get("x-vqd-4")
        if not vqd_token:
            vqd_token = response.headers.get("x-vqd-3")
        
        if vqd_token:
            print(f"[+] VQD Token obtained: {vqd_token}")
            VQD_4_TOKEN = vqd_token
            return vqd_token
        else:
            print(f"[-] VQD Token not found in headers. Headers: {response.headers}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"[-] Error getting VQD token: {e}")
        return None

def send_chat_message(prompt, vqd_token):
    headers = {
        **COMMON_HEADERS,
        "x-ddg-journey-id": "0878452fec48a8ce587f52d3b6e8579a",
        "x-fe-version": "serp_20260810_122611_ET-b35ff7c7f75b035b4c181e313d90924e27775036",
        "x-fe-signals": "eyJzdGFydCI6MTc4NjQxMzc1MDEyNCwiZXZlbnRzIjpbeyJuYW1lIjoic3RhcnROZXdDaGF0X2ZyZWUiLCJkZWx0YSI6MTAwfSx7Im5hbWUiOiJyZWNlbnRDaGF0c0xpc3RJbXByZXNzaW9uIiwiZGVsdGEiOjI4OX0seyJuYW1lIjoiYWN0aW9uIiwiZGVsdGEiOjU2MzE1LCJ0cnVzdGVkIjp0cnVlfV0sImVuZCI6NjAwMDV9",
        "x-vqd-hash-1": "eyJzZXJ2ZXJfaGFzaGVzIjpbIlFYK3Jvb2p2NldvaXRnWkZEeGtHSHV0cWVqTVViZkJFUkp2YkErNHB2bEU9IiwiL1ptS0s5a0hvYXNqUTdhNGF0UXFlK1ZKVjhOOVA1aHo4SEJqbFNPRk13TT0iLCJ5M3NKMHducmU2MTVHM0hJdEdldDFQNk9jK20yaUZiS3JjdFZrZ1NmNlhnPSJdLCJjbGllbnRfaGFzaGVzIjpbIlFKVnZDUGJKcjRPQUxzMGlZNFhHZUtCdm1WNktHZldjMVhXcHBNYXN3b2M9IiwibTFGenVwUGV6VEVmaVZFL0JncGkxbExzR0o4TnVwZmJGY0tnZDRldDBDaz0iLCJIc0NDaGFjbC9sNEJRY3hjeU5TVHMwS2owU3gxcm5PenJOT1R2RHQ5WFRvPSJdLCJzaWduYWxzIjp7fSwibWV0YSI6eyJ2IjoiNCIsImNoYWxsZW5nZV9pZCI6IjZmYzJjZTBkZmY5YWM4OGRiNjc3MzE0N2FlZTAyNzE5Yjg0NzA2MjAzNTdmMTgzODcxY2FjYmE3MzNmZmY1MTdoOGpidCIsInRpbWVzdGFtcCI6IjE3ODY0MTM3NTAyMzYiLCJkZWJ1ZyI6Ilx1MDAxOU8iLCJvcmlnaW4iOiJodHRwczovL2R1Y2suYWkiLCJzdGFjayI6IkVycm9yXG5hdCBsIChodHRwczovL2R1Y2suYWkvZGlzdC9kdWNrYWktZGlzdC9lbnRyeS5kdWNrYWkuNjBkNmRmMjVlM2JkZWRkMDRjNzAuanM6MjoxNzUyMTE4KVxuYXQgYXN5bmMgaHR0cHM6Ly9kdWNrLmFpL2Rpc3QvZHVja2FpLWRpc3QvZW50cnkuZHVja2FpLjYwZDZkZjI1ZTNiZGVkZDA0YzcwLmpzOjI6MTU1NjIxNSIsImR1cmF0aW9uIjoiMTMifX0=",
        "x-vqd-4": vqd_token,
        "accept": "text/event-stream",
        "content-type": "application/json",
        "origin": "https://duck.ai"
    }

    payload = {
        "model": "gpt-5.4-nano",
        "metadata": {
            "toolChoice": {
                "NewsSearch": False,
                "VideosSearch": False,
                "LocalSearch": False,
                "WeatherForecast": False
            }
        },
        "messages": [{"role": "user", "content": prompt}],
        "canUseTools": True,
        "reasoningEffort": "none",
        "canUseApproxLocation": None,
        "canDelegateImageGeneration": None,
        "durableStream": {
            "messageId": str(uuid.uuid4()),
            "conversationId": "1a8f0643-e81f-49bc-a82d-7df50874418e",
            "publicKey": {
                "alg": "RSA-OAEP-256",
                "e": "AQAB",
                "ext": True,
                "key_ops": ["encrypt"],
                "kty": "RSA",
                "n": "pANL1PLHhmGepTU9B-E7ypklzrt5i6EAuE1YnDWjqPqsZm9pW4M62f4M_4sauzO-R3_kMhG1gQgTAKNsn_dSdsJxAdcXFGEs_87rzq2UXHm2Tpak0ag-PuDR0cuW95O4PHZFmoliYEALme6VSzyrc3gYbvz9s7u-Fl5jh9foXfJWWKp1yhv5MQJlgDR1Oy5LCqq686ToJsvjycDfJLbNP-hnFewjLgZda_Z-BQgDXOH7Z9IEsZvo-57Xo3aOsve5jzPIixKakCYqY2eE0td7CYrVMnLAVCn7KgEgsTMlvTBGH0CjT5OrEUbNvaCASrPMCNaIamRtbTwvOb6hZA8vsQ",
                "use": "enc"
            }
        }
    }

    try:
        response = requests.post(CHAT_ENDPOINT, headers=headers, data=json.dumps(payload), stream=True)
        response.raise_for_status()
        
        full_response_content = ""
        for chunk in response.iter_content(chunk_size=None):
            if chunk:
                full_response_content += chunk.decode("utf-8")
        
        parsed_message = parse_sse(full_response_content)
        print(f"[+] Chat response: {parsed_message}")
        return parsed_message
    except requests.exceptions.RequestException as e:
        print(f"[-] Error sending chat message: {e}")
        if e.response is not None:
            print(f"[-] Response body: {e.response.text}")
        return None

def parse_sse(body):
    if not body: return ""
    lines = []
    for line in body.splitlines():
        if line.startswith("data: "):
            data_str = line[6:]
            if data_str == "[DONE]": continue
            try:
                data = json.loads(data_str)
                if "message" in data:
                    lines.append(data["message"])
            except: continue
    return "".join(lines)

if __name__ == "__main__":
    vqd = get_vqd_token()
    if vqd:
        chat_response = send_chat_message("teste retea", vqd)
        if chat_response:
            print("\n[SUCCESS] API-based chat approach works perfectly!")
        else:
            print("\n[FAILED] API-based chat response empty.")
    else:
        print("\n[FAILED] Could not obtain VQD token.")
