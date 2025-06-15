from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict
import threading

app = FastAPI()

class Target(BaseModel):
    target: float

# Shared state
setpoint = 0.0
current_temp = 20.0
lock = threading.Lock()


@app.middleware("http")
async def log_requests(request: Request, call_next):
    body = await request.body()
    print(f"\n--- Incoming request ---")
    print(f"Method: {request.method}")
    print(f"URL: {request.url}")
    print(f"Headers: {dict(request.headers)}")
    print(f"Body: {body.decode('utf-8')}")
    # Rebuild request with buffered body
    async def receive():
        return {"type": "http.request", "body": body}
    request._receive = receive
    response = await call_next(request)
    return response


@app.get("/heater")
def get_status() -> Dict[str, float]:
    global current_temp
    with lock:
        current_temp += (setpoint - current_temp) * 0.1
        return {"setpoint": setpoint, "temperature": current_temp}

@app.post("/heater/set")
async def set_target(request: Request):
    body = await request.json()
    print("Received body:", body)

    global setpoint

    try:
        # Check if body is a list with at least one element
        if (isinstance(body, list) and 
            len(body) > 0 and 
            isinstance(body[0], dict) and 
            "value" in body[0]):
            
            # Extract the first element from the list
            input_arg = body[0]
            
            # Check if it has the expected nested structure
            if (isinstance(input_arg["value"], dict) and 
                "value" in input_arg["value"]):
                
                # Extract the actual temperature value (it comes as a string)
                temp_value = input_arg["value"]["value"]
                
                # Convert string to float
                try:
                    setpoint = float(temp_value)
                    return {"message": "Setpoint updated", "setpoint": setpoint}
                except ValueError:
                    return JSONResponse(status_code=422, content={"error": "Temperature value must be a valid number"})
            else:
                return JSONResponse(status_code=422, content={"error": "Invalid value structure"})
        else:
            return JSONResponse(status_code=422, content={"error": "Expected a list with at least one value object"})
            
    except Exception as e:
        print(f"Error processing request: {e}")
        return JSONResponse(status_code=500, content={"error": "Internal server error"})
