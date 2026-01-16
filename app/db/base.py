# Import all models here để Alembic có thể detect
from app.db.session import Base
from app.models.user import User
from app.models.file import File