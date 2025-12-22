from app import create_app, socketio

app = create_app()

if __name__ == "__main__":
    # SocketIO를 활용하여 실시간 메시징 지원
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)