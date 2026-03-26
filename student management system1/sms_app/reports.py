"""Report generation utilities for the SMS application."""

from typing import List, Tuple


def mark_to_grade(mark: int) -> str:
    """Convert a numeric mark to a letter grade."""
    if mark >= 90:
        return 'A'
    elif mark >= 80:
        return 'B'
    elif mark >= 70:
        return 'C'
    elif mark >= 60:
        return 'D'
    else:
        return 'F'


def build_student_report(
    student_id: str,
    name: str,
    program: str,
    class_name: str,
    marks: List[Tuple[str, str, int]]
) -> dict:
    """
    Build a comprehensive student report.
    
    Args:
        student_id: Student ID
        name: Student name
        program: Program/major
        class_name: Class name
        marks: List of (subject, term, mark) tuples
    
    Returns:
        Dictionary containing report data
    """
    report = {
        'student_id': student_id,
        'name': name,
        'program': program,
        'class_name': class_name,
        'marks': []
    }
    
    total_mark = 0
    for subject, term, mark in marks:
        grade = mark_to_grade(mark)
        report['marks'].append({
            'subject': subject,
            'term': term,
            'mark': mark,
            'grade': grade
        })
        total_mark += mark
    
    if marks:
        report['average_mark'] = total_mark / len(marks)
    else:
        report['average_mark'] = 0
    
    return report


def export_report_to_pdf(report_data: dict, filename: str) -> None:
    """
    Export report data to a PDF file.
    
    Note: This is a placeholder implementation. For full functionality,
    you would need to install a PDF library like reportlab or fpdf.
    
    Args:
        report_data: Dictionary containing report data
        filename: Output filename
    """
    # Placeholder: In a real implementation, you would use a library like reportlab
    # to generate a PDF file. For now, we just pass.
    pass
