import argparse
import os
import warnings

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from uparse import load_model
from uparse.routes.parse import router

warnings.filterwarnings("ignore", category=UserWarning)
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/parse")


def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Run the omniparse server.")
    parser.add_argument("--host", default="0.0.0.0", help="Host IP address")
    parser.add_argument("--port", type=int, default=8000, help="Port number")
    parser.add_argument("--media", action="store_true", help="Enable media model")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    args = parser.parse_args()

    os.environ["http_proxy"] = "http://localhost:7890"
    os.environ["https_proxy"] = "http://localhost:7890"
    load_model(load_media=args.media)

    app.include_router(router, prefix="/parse")

    import uvicorn

    uvicorn.run("server:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
