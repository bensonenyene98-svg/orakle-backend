from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# It must be inside double quotes like this:
SQLALCHEMY_DATABASE_URL = "postgresql://neondb_owner:npg_WZ3YoGKehAJ8@ep-noisy-unit-ab48ypr0-pooler.eu-west-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()