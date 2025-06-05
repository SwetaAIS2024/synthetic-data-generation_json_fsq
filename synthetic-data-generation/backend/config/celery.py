from __future__ import absolute_import
from celery import Celery
from config import Config


app = Celery(
    "kyc_extraction",
    broker=Config.RABBIT_MQ_URL,
    backend="rpc://",
    include=["modules.processor"],
)