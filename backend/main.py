from backend.bootstrap import bootstrap

bootstrap()

import uvicorn


def main() -> None:
    uvicorn.run("backend.app:app", host="0.0.0.0", port=8001, loop="asyncio")


if __name__ == "__main__":
    main()
