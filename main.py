# Определение моделей и базовых настроек
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Boolean, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from pydantic import BaseModel
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from typing import List, Optional
import uuid
from sqlalchemy.sql import and_, or_
from collections import defaultdict, deque
from fastapi import Query

SECRET_KEY = "your_secret_key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

app = FastAPI()

engine = create_engine('sqlite:///booking.db')
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Определение Pydantic-моделей
class FlightOut(BaseModel):
    id: int
    departure_city: str
    arrival_city: str
    departure_time: datetime
    arrival_time: datetime
    price: float
    available_seats: int

    class Config:
        from_attributes = True  

class FlightSearchResult(BaseModel):
    path: List[str]
    flights: List[FlightOut]
    total_price: float
    total_time: float
    category: str | None

    class Config:
        from_attributes = True  

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    name = Column(String)
    hashed_password = Column(String)
    role = Column(String, default="user")

class Hotel(Base):
    __tablename__ = "hotels"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    city = Column(String)
    stars = Column(Integer)
    rooms = relationship("Room", back_populates="hotel")

class Room(Base):
    __tablename__ = "rooms"
    id = Column(Integer, primary_key=True, index=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id"))
    type = Column(String)
    rooms_count = Column(Integer)
    price = Column(Float)
    capacity = Column(Integer)
    hotel = relationship("Hotel", back_populates="rooms")
    bookings = relationship("Booking", back_populates="room")

class Booking(Base):
    __tablename__ = "bookings"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    room_id = Column(Integer, ForeignKey("rooms.id"))
    check_in = Column(DateTime)
    check_out = Column(DateTime)
    user = relationship("User")
    room = relationship("Room", back_populates="bookings")

class Flight(Base):
    __tablename__ = "flights"
    id = Column(Integer, primary_key=True, index=True)
    departure_city = Column(String)
    arrival_city = Column(String)
    departure_time = Column(DateTime)
    arrival_time = Column(DateTime)
    price = Column(Float)
    total_seats = Column(Integer)
    booked_seats = Column(Integer, default=0)

Base.metadata.create_all(bind=engine)

# Определение моделей для входных и выходных данных
class UserCreate(BaseModel):
    email: str
    name: str
    password: str
    role: Optional[str] = "user"

class UserUpdate(BaseModel):
    name: str

class Token(BaseModel):
    access_token: str
    token_type: str

class HotelCreate(BaseModel):
    name: str
    city: str
    stars: int

class HotelOut(BaseModel):
    id: int
    name: str
    city: str
    stars: int

    class Config:
        from_attributes = True  

class RoomCreate(BaseModel):
    hotel_id: int
    type: str
    rooms_count: int
    price: float
    capacity: int

class RoomOut(BaseModel):
    id: int
    hotel_id: int
    type: str
    rooms_count: int
    price: float
    capacity: int

    class Config:
        from_attributes = True  

class BookingCreate(BaseModel):
    room_id: int
    check_in: datetime
    check_out: datetime

class BookingOut(BaseModel):
    id: int
    user_id: int
    room_id: int
    check_in: datetime
    check_out: datetime

    class Config:
        from_attributes = True  

class FlightCreate(BaseModel):
    departure_city: str
    arrival_city: str
    departure_time: datetime
    arrival_time: datetime
    price: float
    total_seats: int

class FlightSearch(BaseModel):
    from_city: str
    to_city: str
    date_from: datetime
    date_to: datetime
    passengers: int = 1
    via_city: Optional[str] = None

# Определение зависимостей и утилит
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    password = password[:72]
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db=Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    return user

async def get_current_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return current_user

# Утилиты для пользователей
@app.post("/register")
def register(user: UserCreate, db=Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = get_password_hash(user.password)
    new_user = User(email=user.email, name=user.name, hashed_password=hashed_password, role=user.role)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"msg": "User created"}

@app.post("/token", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db=Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.put("/user/update")
def update_user(update: UserUpdate, current_user: User = Depends(get_current_user), db=Depends(get_db)):
    current_user.name = update.name
    db.commit()
    return {"msg": "Name updated"}

# Утилиты для отелей
@app.post("/hotels", response_model=HotelOut)
def create_hotel(hotel: HotelCreate, admin: User = Depends(get_current_admin), db=Depends(get_db)):
    new_hotel = Hotel(**hotel.dict())
    db.add(new_hotel)
    db.commit()
    db.refresh(new_hotel)
    return new_hotel

@app.get("/hotels", response_model=List[HotelOut])
def get_hotels(city: Optional[str] = None, stars: Optional[int] = None, order_by_stars: Optional[str] = None, db=Depends(get_db)):
    query = db.query(Hotel)
    if city:
        query = query.filter(Hotel.city == city)
    if stars:
        query = query.filter(Hotel.stars == stars)
    if order_by_stars == "asc":
        query = query.order_by(Hotel.stars)
    elif order_by_stars == "desc":
        query = query.order_by(Hotel.stars.desc())
    return query.all()

@app.put("/hotels/{hotel_id}", response_model=HotelOut)
def update_hotel(hotel_id: int, hotel: HotelCreate, admin: User = Depends(get_current_admin), db=Depends(get_db)):
    db_hotel = db.query(Hotel).filter(Hotel.id == hotel_id).first()
    if not db_hotel:
        raise HTTPException(status_code=404, detail="Hotel not found")
    for key, value in hotel.dict().items():
        setattr(db_hotel, key, value)
    db.commit()
    db.refresh(db_hotel)
    return db_hotel

@app.delete("/hotels/{hotel_id}")
def delete_hotel(hotel_id: int, admin: User = Depends(get_current_admin), db=Depends(get_db)):
    db_hotel = db.query(Hotel).filter(Hotel.id == hotel_id).first()
    if not db_hotel:
        raise HTTPException(status_code=404, detail="Hotel not found")
    db.delete(db_hotel)
    db.commit()
    return {"msg": "Hotel deleted"}

# Утилиты для комнат
@app.post("/rooms", response_model=RoomOut)
def create_room(room: RoomCreate, admin: User = Depends(get_current_admin), db=Depends(get_db)):
    new_room = Room(**room.dict())
    db.add(new_room)
    db.commit()
    db.refresh(new_room)
    return new_room

@app.get("/rooms", response_model=List[RoomOut])
def get_rooms(hotel_id: Optional[int] = None, rooms_count: Optional[int] = None, type: Optional[str] = None, 
              price_min: Optional[float] = None, price_max: Optional[float] = None, capacity: Optional[int] = None, 
              order_by_price: Optional[str] = None, db=Depends(get_db)):
    query = db.query(Room)
    if hotel_id:
        query = query.filter(Room.hotel_id == hotel_id)
    if rooms_count:
        query = query.filter(Room.rooms_count == rooms_count)
    if type:
        query = query.filter(Room.type == type)
    if price_min:
        query = query.filter(Room.price >= price_min)
    if price_max:
        query = query.filter(Room.price <= price_max)
    if capacity:
        query = query.filter(Room.capacity == capacity)
    if order_by_price == "asc":
        query = query.order_by(Room.price)
    elif order_by_price == "desc":
        query = query.order_by(Room.price.desc())
    return query.all()

@app.put("/rooms/{room_id}", response_model=RoomOut)
def update_room(room_id: int, room: RoomCreate, admin: User = Depends(get_current_admin), db=Depends(get_db)):
    db_room = db.query(Room).filter(Room.id == room_id).first()
    if not db_room:
        raise HTTPException(status_code=404, detail="Room not found")
    for key, value in room.dict().items():
        setattr(db_room, key, value)
    db.commit()
    db.refresh(db_room)
    return db_room

@app.delete("/rooms/{room_id}")
def delete_room(room_id: int, admin: User = Depends(get_current_admin), db=Depends(get_db)):
    db_room = db.query(Room).filter(Room.id == room_id).first()
    if not db_room:
        raise HTTPException(status_code=404, detail="Room not found")
    db.delete(db_room)
    db.commit()
    return {"msg": "Room deleted"}

# Утилиты для бронирования
def is_room_available(db, room_id, check_in, check_out):
    overlapping = db.query(Booking).filter(
        Booking.room_id == room_id,
        or_(
            and_(Booking.check_in < check_out, Booking.check_out > check_in)
        )
    ).count()
    return overlapping == 0

@app.post("/bookings/by_dates", response_model=BookingOut)
def book_by_dates(booking: BookingCreate, current_user: User = Depends(get_current_user), db=Depends(get_db)):
    if not is_room_available(db, booking.room_id, booking.check_in, booking.check_out):
        raise HTTPException(status_code=400, detail="Room not available")
    new_booking = Booking(user_id=current_user.id, room_id=booking.room_id, check_in=booking.check_in, check_out=booking.check_out)
    db.add(new_booking)
    db.commit()
    db.refresh(new_booking)
    return new_booking

@app.post("/bookings/by_days")
def book_by_days(room_id: int, check_in: datetime, days: int, current_user: User = Depends(get_current_user), db=Depends(get_db)):
    check_out = check_in + timedelta(days=days)
    if not is_room_available(db, room_id, check_in, check_out):
        raise HTTPException(status_code=400, detail="Room not available")
    new_booking = Booking(user_id=current_user.id, room_id=room_id, check_in=check_in, check_out=check_out)
    db.add(new_booking)
    db.commit()
    db.refresh(new_booking)
    return new_booking

@app.get("/available_rooms", response_model=List[RoomOut])
def get_available_rooms(
    check_in: datetime,
    check_out: datetime,
    hotel_id: Optional[int] = None,
    type: Optional[str] = None,
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
    capacity: Optional[int] = None,
    order_by_price: Optional[str] = None,
    db=Depends(get_db)
):
    query = db.query(Room)
    
    if hotel_id is not None:
        query = query.filter(Room.hotel_id == hotel_id)
    
    if type is not None:
        query = query.filter(Room.type == type)
    
    if price_min is not None:
        query = query.filter(Room.price >= price_min)
    if price_max is not None:
        query = query.filter(Room.price <= price_max)
    
    if capacity is not None:
        query = query.filter(Room.capacity == capacity)
    
    rooms = query.all()
    available_rooms = []
    
    for room in rooms:
        if is_room_available(db, room.id, check_in, check_out):
            available_rooms.append(room)
    
    if order_by_price == "asc":
        available_rooms.sort(key=lambda x: x.price)
    elif order_by_price == "desc":
        available_rooms.sort(key=lambda x: x.price, reverse=True)
    
    return available_rooms

@app.delete("/bookings/{booking_id}")
def cancel_booking(booking_id: int, current_user: User = Depends(get_current_user), db=Depends(get_db)):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if current_user.role != "admin" and booking.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    db.delete(booking)
    db.commit()
    return {"msg": "Booking canceled"}

# Утилиты маршрутов для рейсов
@app.post("/flights", response_model=FlightOut)
def create_flight(flight: FlightCreate, admin: User = Depends(get_current_admin), db=Depends(get_db)):
    new_flight = Flight(**flight.dict(), booked_seats=0)
    db.add(new_flight)
    db.commit()
    db.refresh(new_flight)
    return FlightOut(**new_flight.__dict__, available_seats=new_flight.total_seats - new_flight.booked_seats)

@app.get("/flights", response_model=List[FlightOut])
def get_flights(db=Depends(get_db)):
    flights = db.query(Flight).all()
    return [FlightOut(**f.__dict__, available_seats=f.total_seats - f.booked_seats) for f in flights]

@app.put("/flights/{flight_id}", response_model=FlightOut)
def update_flight(flight_id: int, flight: FlightCreate, admin: User = Depends(get_current_admin), db=Depends(get_db)):
    db_flight = db.query(Flight).filter(Flight.id == flight_id).first()
    if not db_flight:
        raise HTTPException(status_code=404, detail="Flight not found")
    for key, value in flight.dict().items():
        setattr(db_flight, key, value)
    db.commit()
    db.refresh(db_flight)
    return FlightOut(**db_flight.__dict__, available_seats=db_flight.total_seats - db_flight.booked_seats)

@app.delete("/flights/{flight_id}")
def delete_flight(flight_id: int, admin: User = Depends(get_current_admin), db=Depends(get_db)):
    db_flight = db.query(Flight).filter(Flight.id == flight_id).first()
    if not db_flight:
        raise HTTPException(status_code=404, detail="Flight not found")
    db.delete(db_flight)
    db.commit()
    return {"msg": "Flight deleted"}

# Функция поиска путей
def find_shortest_paths(db, from_city, to_city, date_from, date_to, passengers, via_city=None):
    all_flights = db.query(Flight).filter(
        Flight.departure_time >= date_from,
        Flight.departure_time <= date_to,
        Flight.total_seats - Flight.booked_seats >= passengers
    ).all()
    
    graph = {}
    for f in all_flights:
        if f.departure_city not in graph:
            graph[f.departure_city] = []
        graph[f.departure_city].append(f)
    
    queue = deque([([from_city], [], 0)])
    visited = set()
    paths = []
    
    while queue:
        path, flights, total_time = queue.popleft()
        current = path[-1]
        if current == to_city:
            if via_city and via_city not in path:
                continue
            paths.append((path, flights, total_time))
            continue
        
        if current in visited:
            continue
        visited.add(current)
        
        if current not in graph:
            continue
        
        for flight in sorted(graph[current], key=lambda f: f.departure_time):
            if flight.arrival_city in path:
                continue
            layover = 0
            if flights:
                prev_arrival = flights[-1].arrival_time
                if flight.departure_time - prev_arrival > timedelta(hours=24):
                    continue
                layover = (flight.departure_time - prev_arrival).total_seconds() / 3600
            new_total_time = total_time + (flight.arrival_time - flight.departure_time).total_seconds() / 3600 + layover
            queue.append((path + [flight.arrival_city], flights + [flight], new_total_time))
    
    if not paths:
        return []
    
    results = []
    for path, flights, total_time in paths:
        total_price = sum(f.price for f in flights)
        results.append({
            "path": path,
            "flights": [FlightOut(**f.__dict__, available_seats=f.total_seats - f.booked_seats) for f in flights],
            "total_price": total_price,
            "total_time": total_time,
            "category": None
        })
    
    return results

# Утилита для поиска рейсов
@app.post("/flights/search", response_model=List[FlightSearchResult])
def search_flights(
    search_data: FlightSearch,
    order_by: Optional[str] = Query(None, description="Sort by: price_asc, price_desc"),
    order_by_time: Optional[str] = Query(None, description="Sort by: time_asc, time_desc"),
    db=Depends(get_db)
):
    from_city = search_data.from_city
    to_city = search_data.to_city
    date_from = search_data.date_from
    date_to = search_data.date_to
    passengers = search_data.passengers
    via_city = search_data.via_city

    results = find_shortest_paths(db, from_city, to_city, date_from, date_to, passengers, via_city)

    if results:
        fastest_time = min(r["total_time"] for r in results)
        cheapest_price = min(r["total_price"] for r in results)
        for result in results:
            if result["total_time"] == fastest_time:
                result["category"] = "fastest"
            elif result["total_price"] == cheapest_price:
                result["category"] = "cheapest"

    if order_by_time:
        if order_by_time == "time_asc":
            results.sort(key=lambda x: x["flights"][0].departure_time if x["flights"] else datetime.max)
        elif order_by_time == "time_desc":
            results.sort(key=lambda x: x["flights"][0].departure_time if x["flights"] else datetime.min, reverse=True)
    elif order_by:
        if order_by == "price_asc":
            results.sort(key=lambda x: x["total_price"])
        elif order_by == "price_desc":
            results.sort(key=lambda x: x["total_price"], reverse=True)
    else:
        def sort_key(item):
            if item["category"] == "fastest":
                return (0, item["total_price"])
            elif item["category"] == "cheapest":
                return (1, item["total_price"])
            else:
                return (2, item["total_price"])
        results.sort(key=sort_key)

    return results

#Утилита для бронирования билетов
@app.post("/flights/book/{flight_id}")
def book_flight(flight_id: int, passengers: int, current_user: User = Depends(get_current_user), db=Depends(get_db)):
    flight = db.query(Flight).filter(Flight.id == flight_id).first()
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")
    if flight.total_seats - flight.booked_seats < passengers:
        raise HTTPException(status_code=400, detail="Not enough seats")
    flight.booked_seats += passengers
    db.commit()
    return {"msg": "Flight booked"}