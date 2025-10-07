import asyncio
import datetime
import json
import os
import random
import time
from typing import Any, Iterator, List, Optional

from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel

app = FastAPI()

TOTAL_PAGES: int = random.randint(500, 600)
PAGE_SIZE: int = 10
CHAOS_PERCENT: int = 2


class BaseAnimal(BaseModel):
    id: int
    name: str
    born_at: Optional[int]


class Animal(BaseAnimal):
    friends: str


class IncomingAnimal(BaseAnimal):
    friends: List[str]
    born_at: Optional[datetime.datetime]


class ListingMeta(BaseModel):
    page: int
    total_pages: int
    items: List[Any]


class Animals(ListingMeta):
    items: List[BaseAnimal]


def generate_animals() -> Iterator[Animal]:
    now = int(time.time() * 1000)

    with open("animals.json") as f:
        animal_names = json.load(f)

    for i in range(TOTAL_PAGES * PAGE_SIZE):
        born_at = None
        if random.randint(0, 5) == 1:
            born_at = random.randint(536461200 * 1000, now)

        yield Animal(
            id=i,
            name=random.choice(animal_names),
            born_at=born_at,
            friends=",".join(random.sample(animal_names, random.randint(0, 5))),
        )


ANIMALS = list(generate_animals())
VERIFY = os.getenv("VERIFY") == "1"
if VERIFY is True:
    ANIMALS_IDS_TO_VERIFY = {a.id for a in ANIMALS}


@app.get("/animals/v1/animals", response_model=Animals)
def get_animals(page: int = 1):
    start_index = PAGE_SIZE * (page - 1)
    end_index = start_index + PAGE_SIZE
    animals = ANIMALS[start_index:end_index]
    animals = [a.dict(exclude={"friends"}) for a in animals]
    return Animals(
        items=animals,
        page=page,
        total_pages=TOTAL_PAGES,
    )


@app.get("/animals/v1/animals/{animal_id}", response_model=Animal)
def get_animal(animal_id: int):
    return ANIMALS[animal_id]


@app.post("/animals/v1/home")
def receive_animals(animals: List[IncomingAnimal]):
    if len(animals) > 100:
        raise HTTPException(status_code=400, detail="Sorry, only 100 animals at a time")
    if VERIFY is True:
        for animal in animals:
            ANIMALS_IDS_TO_VERIFY.remove(animal.id)
        print(f"{len(ANIMALS_IDS_TO_VERIFY)} animals left")
    return {"message": f"Helped {len(animals)} find home"}


@app.get("/")
def index():
    return "Hello!"


@app.middleware("http")
async def chaos_middleware(request: Request, call_next):
    path = request.scope["path"]
    if path != "/" and random.randint(0, 100) < CHAOS_PERCENT:
        failure_type = random.randint(0, 1)
        if failure_type == 0:
            return Response(
                status_code=random.choice((500, 502, 503, 504)),
                content=b"Sorry!",
            )
        else:
            await asyncio.sleep(random.randint(5, 15))

    return await call_next(request)
