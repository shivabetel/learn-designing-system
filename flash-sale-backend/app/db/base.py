from sqlalchemy.orm import DeclarativeBase, declared_attr
class Base(DeclarativeBase):
    """ this is the base class for all models """

    @declared_attr.directive
    def __tablename__(cls):
        """ 
        get the table name of the model
        """
        return cls.__name__.lower()
