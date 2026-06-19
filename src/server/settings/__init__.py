from .settings import EnvSettings, PhysicsSettings, PlayerSettings

from dotenv import load_dotenv


load_dotenv()


config = EnvSettings()
phys = PhysicsSettings()
player = PlayerSettings()
