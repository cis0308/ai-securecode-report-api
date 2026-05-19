from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.database import Base

class AnalysisFinding(Base):
    __tablename__ = "analysis_findings"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), nullable=True)
    filename = Column(String(255), nullable=False)
    test_id = Column(String(100), nullable=True)
    test_name = Column(String(255), nullable=False)
    issue_severity = Column(String(20), nullable=False, default="LOW")
    issue_confidence = Column(String(20), nullable=True)
    cwe = Column(String(50), nullable=True)
    mois = Column(String(255), nullable=True)
    file_path = Column(String(500), nullable=True)
    line_number = Column(Integer, nullable=True)
    score = Column(Integer, nullable=True)
    grade = Column(String(5), nullable=True)
    report_path = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
