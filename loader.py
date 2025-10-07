import uvicorn

if __name__ == "__main__":
    uvicorn.run("animal_api:app", host="0.0.0.0", port=3123, reload=True)
