from numpy import add
import models
import yfinance
from fastapi import FastAPI, Request, Depends, BackgroundTasks
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import SessionLocal, engine
from pydantic import BaseModel
from models import Stock

fastapi = FastAPI

models.Base.metadata.create_all(bind=engine)

templates = Jinja2Templates(directory="templates")

app = fastapi()


class StockRequest(BaseModel):
    symbol: str

def get_db():
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()

@app.get("/")
def home(request: Request, forward_pe = None, dividend_yield = None, ma50 = None, ma200 = None, db: Session = Depends(get_db)):
    """
    displays the home page
    """
    stocks = db.query(Stock)

    print(stocks)

    if forward_pe:
        stocks = stocks.filter(Stock.forward_pe < forward_pe)

    if dividend_yield:
        stocks = stocks.filter(Stock.dividend_yield > dividend_yield)

    if ma50:
        stocks = stocks.filter(Stock.price > Stock.ma50)

    if ma200:
        stocks = stocks.filter(Stock.price > Stock.ma200)

    return templates.TemplateResponse("home.html", {
        "request": request,
        "stocks": stocks,
        "dividend_yield": dividend_yield,
        "ma50": ma50,
        "ma200": ma200,
    })

def fetch_stock_data(id: int):
    db = SessionLocal()
    stock = db.query(Stock).filter(Stock.id ==id).first()

    stock_data = yfinance.Ticker(stock.symbol)

    stock.ma200 = stock_data.info['twoHundredDayAverage']
    stock.m50 = stock_data.info['fiftyDayAverage']
    stock.price = stock_data.info['previousClose']
    stock.forward_pe = stock_data.info['forwardPE']
    stock.forward_eps = stock_data.info['forwardEps']
    if stock_data.info['dividendYield'] is not None:
        stock.dividend_yield = stock_data.info['dividendYield'] 

    db.add(stock)
    db.commit()

@app.post("/stock")
async def create_stock(stock_request: StockRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    create the stock and stores it on the db
    """
    stock = Stock()
    stock.symbol = stock_request.symbol

    db.add(stock)
    db.commit()

    background_tasks.add_task(fetch_stock_data, stock.id)

    return{
        "code": "sucess",
        "message": "stock created"
    }