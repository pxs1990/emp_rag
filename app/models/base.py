from sqlalchemy.orm import declarative_base

# All ORM models import Base from here so they share one MetaData object.
# Call Base.metadata.create_all(engine) to create all tables at once.
Base = declarative_base()
