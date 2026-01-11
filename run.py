"""应用入口"""
from app import create_app
import config

app = create_app()

if __name__ == '__main__':
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)

