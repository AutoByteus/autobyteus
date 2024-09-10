from autobyteus.person.examples.sample_roles import RESEARCHER_ROLE, WRITER_ROLE
from autobyteus.person.person import Person

ANNA = Person(
    name="Anna",
    role=RESEARCHER_ROLE,
    characteristics=["detail-oriented", "analytical", "curious"]
)

RYAN = Person(
    name="Ryan",
    role=WRITER_ROLE,
    characteristics=["creative", "empathetic", "articulate"]
)