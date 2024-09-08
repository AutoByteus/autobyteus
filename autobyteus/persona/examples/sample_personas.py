


from autobyteus.persona.examples.sample_roles import RESEARCHER_ROLE, WRITER_ROLE
from autobyteus.persona.persona import Persona


ANNA = Persona(
    name="Anna",
    role=RESEARCHER_ROLE,
    characteristics=["detail-oriented", "analytical", "curious"]
)

RYAN = Persona(
    name="Ryan",
    role=WRITER_ROLE,
    characteristics=["creative", "empathetic", "articulate"]
)