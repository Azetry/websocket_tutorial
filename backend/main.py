from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Optional
import json
import logging

app = FastAPI()

# 添加 CORS 中間件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生產環境中應該設置具體的源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 存儲活動連接的字典
active_connections: Dict[str, WebSocket] = {}

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await websocket.accept()
    active_connections[client_id] = websocket
    logging.info("Client %s connected. Current online clients: %s", 
                client_id, list(active_connections.keys()))
    
    try:
        while True:
            # 等待接收消息
            message = await websocket.receive_text()
            data = json.loads(message)
            
            # 確保消息包含必要的字段
            if "recipient_id" in data and "content" in data:
                recipient_ws = active_connections.get(data["recipient_id"])
                if recipient_ws:
                    # 發送消息給接收者
                    await recipient_ws.send_json({
                        "sender_id": client_id,
                        "content": data["content"],
                        "timestamp": data.get("timestamp")
                    })
                    # 發送確認消息給發送者
                    await websocket.send_json({
                        "status": "delivered",
                        "recipient_id": data["recipient_id"],
                        "content": data["content"],
                        "timestamp": data.get("timestamp")
                    })
                else:
                    # 如果接收者不在線
                    await websocket.send_json({
                        "status": "error",
                        "message": "Recipient not found or offline"
                    })
            
    except WebSocketDisconnect:
        # 當客戶端斷開連接時，從活動連接中移除
        if client_id in active_connections:
            logging.info("Client %s disconnected. Current online clients: %s", 
                        client_id, list(active_connections.keys()))
            del active_connections[client_id]
    
    except Exception as e:
        print(f"Error: {str(e)}")
        if client_id in active_connections:
            del active_connections[client_id]

# 用於檢查用戶在線狀態的端點
@app.get("/status/{client_id}")
async def get_client_status(client_id: str):
    return {"online": client_id in active_connections}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)