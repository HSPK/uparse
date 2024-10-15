import argparse
import warnings

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from uparse import get_all_models
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
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    parser.add_argument("--workers", type=int, default=1, help="Number of workers")
    args = parser.parse_args()

    get_all_models()

    app.include_router(router, prefix="/parse")

    import uvicorn

    uvicorn.run(
        "server:app", host=args.host, port=args.port, reload=args.reload, workers=args.workers
    )


if __name__ == "__main__":
    main()
