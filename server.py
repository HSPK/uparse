import argparse
import warnings

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from uparse import get_all_models
from uparse.routes.parse import router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def on_app_startup():
    warnings.filterwarnings("ignore", category=UserWarning)
    warnings.filterwarnings("ignore", category=FutureWarning)
    get_all_models()


app.include_router(router, prefix="/parse")
app.add_event_handler("startup", on_app_startup)


def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Run the omniparse server.")
    parser.add_argument("--host", default="0.0.0.0", help="Host IP address")
    parser.add_argument("--port", type=int, default=8000, help="Port number")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    parser.add_argument("--workers", type=int, default=1, help="Number of workers")
    args = parser.parse_args()

    import uvicorn

    uvicorn.run("server:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
