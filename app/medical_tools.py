import json
import math
from typing import Dict, Any, Optional
from datetime import datetime
import random

class MedicalFunctionTools:
    """
    Medical function calling tools based on your MediAssist domain.
    Demonstrates complex interaction beyond simple Q&A.
    """
    
    @staticmethod
    def get_available_functions() -> Dict[str, Dict[str, Any]]:
        """
        Define available medical functions for LLM tool calling.
        Based on your MediAssist medical domain.
        
        Returns:
            Dictionary of function definitions
        """
        return {
            "calculate_bmi": {
                "name": "calculate_bmi",
                "description": "Calculate Body Mass Index (BMI) from weight and height",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "weight_kg": {
                            "type": "number",
                            "description": "Weight in kilograms"
                        },
                        "height_cm": {
                            "type": "number",
                            "description": "Height in centimeters"
                        }
                    },
                    "required": ["weight_kg", "height_cm"]
                }
            },
            "calculate_dosage": {
                "name": "calculate_dosage",
                "description": "Calculate medication dosage based on weight and condition",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "medication": {
                            "type": "string",
                            "description": "Medication name",
                            "enum": ["paracetamol", "ibuprofen", "aspirin", "metformin"]
                        },
                        "weight_kg": {
                            "type": "number",
                            "description": "Patient weight in kilograms"
                        },
                        "condition": {
                            "type": "string",
                            "description": "Medical condition",
                            "enum": ["fever", "pain", "inflammation", "diabetes"]
                        },
                        "age_years": {
                            "type": "integer",
                            "description": "Patient age in years"
                        }
                    },
                    "required": ["medication", "weight_kg", "condition"]
                }
            },
            "check_symptoms": {
                "name": "check_symptoms",
                "description": "Analyze symptoms and suggest possible conditions",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "symptoms": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of symptoms reported by patient"
                        },
                        "duration_days": {
                            "type": "integer",
                            "description": "How long symptoms have persisted (days)"
                        },
                        "severity": {
                            "type": "string",
                            "description": "Symptom severity",
                            "enum": ["mild", "moderate", "severe"]
                        }
                    },
                    "required": ["symptoms"]
                }
            },
            "get_medical_guidelines": {
                "name": "get_medical_guidelines",
                "description": "Fetch medical guidelines for specific conditions",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "condition": {
                            "type": "string",
                            "description": "Medical condition",
                            "enum": ["diabetes", "hypertension", "asthma", "covid", "flu"]
                        },
                        "patient_type": {
                            "type": "string",
                            "description": "Type of patient",
                            "enum": ["adult", "child", "elderly", "pregnant"]
                        }
                    },
                    "required": ["condition"]
                }
            },
            "schedule_appointment": {
                "name": "schedule_appointment",
                "description": "Schedule a medical appointment",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "specialty": {
                            "type": "string",
                            "description": "Medical specialty",
                            "enum": ["general", "cardiology", "endocrinology", "pediatrics"]
                        },
                        "urgency": {
                            "type": "string",
                            "description": "Appointment urgency",
                            "enum": ["routine", "urgent", "emergency"]
                        },
                        "preferred_date": {
                            "type": "string",
                            "description": "Preferred date (YYYY-MM-DD)"
                        }
                    },
                    "required": ["specialty", "urgency"]
                }
            }
        }
    
    @staticmethod
    async def execute_function(function_name: str, arguments: Dict[str, Any]) -> str:
        """
        Execute a medical function and return result.
        
        Args:
            function_name: Name of function to execute
            arguments: Function arguments
            
        Returns:
            Function execution result as string
        """
        try:
            if function_name == "calculate_bmi":
                return MedicalFunctionTools._calculate_bmi(**arguments)
            elif function_name == "calculate_dosage":
                return MedicalFunctionTools._calculate_dosage(**arguments)
            elif function_name == "check_symptoms":
                return MedicalFunctionTools._check_symptoms(**arguments)
            elif function_name == "get_medical_guidelines":
                return MedicalFunctionTools._get_medical_guidelines(**arguments)
            elif function_name == "schedule_appointment":
                return MedicalFunctionTools._schedule_appointment(**arguments)
            else:
                return f"Unknown function: {function_name}"
        except Exception as e:
            return f"Error executing {function_name}: {str(e)}"
    
    @staticmethod
    def _calculate_bmi(weight_kg: float, height_cm: float) -> str:
        """Calculate BMI and provide interpretation"""
        height_m = height_cm / 100
        bmi = weight_kg / (height_m ** 2)
        
        if bmi < 18.5:
            category = "Underweight"
            recommendation = "Consider consulting a nutritionist"
        elif bmi < 25:
            category = "Normal weight"
            recommendation = "Maintain healthy diet and exercise"
        elif bmi < 30:
            category = "Overweight"
            recommendation = "Consider weight management program"
        else:
            category = "Obese"
            recommendation = "Consult healthcare provider for guidance"
        
        return f"BMI: {bmi:.1f} ({category})\nCategory: {category}\nRecommendation: {recommendation}"
    
    @staticmethod
    def _calculate_dosage(medication: str, weight_kg: float, condition: str, age_years: Optional[int] = None) -> str:
        """Calculate medication dosage"""
        dosages = {
            "paracetamol": {
                "fever": f"{15 * weight_kg:.0f}mg every 4-6 hours (max {60 * weight_kg:.0f}mg daily)",
                "pain": f"{10 * weight_kg:.0f}mg every 4-6 hours"
            },
            "ibuprofen": {
                "inflammation": f"{5 * weight_kg:.0f}mg every 6-8 hours",
                "pain": f"{5 * weight_kg:.0f}mg every 6-8 hours"
            },
            "metformin": {
                "diabetes": "500mg twice daily with meals"
            }
        }
        
        if medication not in dosages:
            return f"No dosage information available for {medication}"
        
        if condition not in dosages[medication]:
            return f"{medication} not typically used for {condition}"
        
        dosage = dosages[medication][condition]
        
        if age_years and age_years < 12:
            return f"Pediatric dosage for {age_years}y: {dosage}\n⚠️ Always consult pediatrician"
        
        warnings = []
        if medication == "ibuprofen" and condition == "inflammation":
            warnings.append("Take with food to avoid stomach upset")
        if medication == "metformin":
            warnings.append("Monitor blood sugar levels regularly")
        
        warning_text = "\n".join(warnings) if warnings else "No specific warnings"
        
        return f"""Medication: {medication}
Condition: {condition}
Recommended Dosage: {dosage}
Weight-based: {weight_kg}kg
Warnings: {warning_text}
⚠️ IMPORTANT: This is for educational purposes. Always follow doctor's prescription."""
    
    @staticmethod
    def _check_symptoms(symptoms: list, duration_days: Optional[int] = None, severity: str = "moderate") -> str:
        """Analyze symptoms and suggest possible conditions"""
        symptom_db = {
            "fever": ["flu", "covid", "infection"],
            "cough": ["flu", "covid", "asthma", "bronchitis"],
            "headache": ["migraine", "tension headache", "sinusitis"],
            "fatigue": ["anemia", "thyroid issues", "chronic fatigue"],
            "chest pain": ["angina", "heartburn", "anxiety"],
            "shortness of breath": ["asthma", "anxiety", "heart condition"]
        }
        
        possible_conditions = set()
        for symptom in symptoms:
            if symptom.lower() in symptom_db:
                possible_conditions.update(symptom_db[symptom.lower()])
        
        if not possible_conditions:
            possible_conditions = ["viral infection", "general illness"]
        
        duration_info = f"Symptoms for {duration_days} days. " if duration_days else ""
        severity_info = f"Severity: {severity}. "
        
        advice = "Self-care recommended" if severity == "mild" else "Consult healthcare provider"
        if severity == "severe" or "chest pain" in symptoms or "shortness of breath" in symptoms:
            advice = "Seek immediate medical attention"
        
        return f"""Symptom Analysis:
Reported Symptoms: {', '.join(symptoms)}
{duration_info}{severity_info}
Possible Conditions: {', '.join(sorted(possible_conditions))}
Recommendation: {advice}
⚠️ This is not a diagnosis. Always consult a healthcare professional."""
    
    @staticmethod
    def _get_medical_guidelines(condition: str, patient_type: str = "adult") -> str:
        """Provide medical guidelines for conditions"""
        guidelines = {
            "diabetes": {
                "adult": """ADA Guidelines for Diabetes Management:
1. Target HbA1c: <7.0% for most adults
2. Blood Pressure: <140/90 mmHg
3. LDL Cholesterol: <100 mg/dL
4. Exercise: 150 mins/week moderate activity
5. Diet: Low glycemic index, high fiber""",
                "elderly": """ADA Guidelines for Elderly with Diabetes:
1. Target HbA1c: <7.5-8.0% based on health status
2. Focus on avoiding hypoglycemia
3. Regular foot exams
4. Annual eye exams
5. Individualized treatment plans"""
            },
            "hypertension": {
                "adult": """AHA Hypertension Guidelines:
1. Target BP: <130/80 mmHg
2. Lifestyle: DASH diet, reduce sodium
3. Exercise: 30 mins daily
4. Limit alcohol: 1-2 drinks/day max
5. Regular monitoring"""
            },
            "asthma": {
                "adult": """GINA Asthma Guidelines:
1. Use controller medication daily
2. Carry rescue inhaler always
3. Avoid triggers: pollen, dust, smoke
4. Peak flow monitoring
5. Action plan for exacerbations""",
                "child": """Pediatric Asthma Guidelines:
1. Use spacer with inhaler
2. Monitor growth and development
3. School action plan
4. Regular follow-up every 3-6 months
5. Vaccination: Annual flu shot"""
            }
        }
        
        if condition not in guidelines:
            return f"No specific guidelines found for {condition}"
        
        if patient_type not in guidelines[condition]:
            return f"""Guidelines for {condition} (General):
{guidelines[condition].get('adult', 'No guidelines available')}"""
        
        return guidelines[condition][patient_type]
    
    @staticmethod
    def _schedule_appointment(specialty: str, urgency: str, preferred_date: Optional[str] = None) -> str:
        """Schedule a medical appointment"""
        from datetime import datetime, timedelta
        
        # Simulate appointment scheduling
        appointment_slots = {
            "general": ["9:00 AM", "11:00 AM", "2:00 PM", "4:00 PM"],
            "cardiology": ["10:00 AM", "1:00 PM", "3:00 PM"],
            "endocrinology": ["9:30 AM", "2:30 PM"],
            "pediatrics": ["8:00 AM", "10:30 AM", "1:30 PM", "3:30 PM"]
        }
        
        if specialty not in appointment_slots:
            return f"Specialty {specialty} not available"
        
        slots = appointment_slots[specialty]
        available_slot = random.choice(slots)
        
        date_str = preferred_date or (datetime.now() + timedelta(days=1 if urgency == "routine" else 0)).strftime("%Y-%m-%d")
        
        return f"""Appointment Scheduled:
Specialty: {specialty}
Urgency: {urgency}
Date: {date_str}
Time: {available_slot}
Confirmation Code: APPT-{random.randint(10000, 99999)}
Instructions: Arrive 15 minutes early, bring insurance card and ID"""