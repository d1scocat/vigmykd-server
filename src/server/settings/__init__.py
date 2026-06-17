from .settings import EnvSettings, PhysicsSettings

from dotenv import load_dotenv


load_dotenv()


config = EnvSettings()
phys = PhysicsSettings()
