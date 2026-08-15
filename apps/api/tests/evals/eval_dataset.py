"""Test scenario dataset definitions for BuildSense E2E evaluation suite.
"""

from typing import Any, Dict, List, Optional, TypedDict

class MockLLMCall(TypedDict):
    node: str             # The node or sub-method being mocked
    response_content: str # The text or JSON string response

class Turn(TypedDict):
    user_input: str
    expected_status: str
    expected_components: Dict[str, Any]
    mock_llm_responses: List[MockLLMCall]
    clarification_turns: Optional[int] # Override state.clarification_turns before running this turn

class EvalScenario(TypedDict):
    name: str
    mode: str
    motivation: str
    company_context: Dict[str, str]
    backstory: str
    turns: List[Turn]
    expect_synthesis: bool
    user_constraints: Optional[List[str]]
    initial_turns_count: Optional[int]
    expected_report_contains: List[str]

GOLDEN_SCENARIOS: List[EvalScenario] = [
    {
        "name": "Short Starter Chip Clarification",
        "mode": "OPTIMIZER",
        "motivation": "EDUCATION",
        "company_context": {},
        "backstory": "",
        "expect_synthesis": False,
        "user_constraints": None,
        "expected_report_contains": [],
        "turns": [
            {
                "user_input": "Walk through customer order",
                "expected_status": "AWAITING_CLARIFICATION",
                "expected_components": {
                    "trigger": "User request",
                    "actor": "Staff",
                    "activity": "Workflow task",
                    "system": None,
                    "friction": None
                },
                "clarification_turns": None,
                "mock_llm_responses": [
                    {
                        "node": "sanitize_input",
                        "response_content": "Walk through customer order"
                    },
                    {
                        "node": "extractor",
                        "response_content": '{"trigger": "User request", "actor": "Staff", "activity": "Workflow task", "system": null, "friction": null}'
                    },
                    {
                        "node": "question_generator",
                        "response_content": "What app, tool, notebook, or other place do you use to keep track of it?"
                    }
                ]
            }
        ]
    },
    {
        "name": "Messy Multi-Turn Intake Accumulation",
        "mode": "OPTIMIZER",
        "motivation": "REVENUE",
        "company_context": {},
        "backstory": "",
        "expect_synthesis": False,
        "user_constraints": None,
        "expected_report_contains": [],
        "turns": [
            {
                "user_input": "I run a pet shop",
                "expected_status": "AWAITING_CLARIFICATION",
                "expected_components": {
                    "actor": "Pet shop staff"
                },
                "clarification_turns": 0,
                "mock_llm_responses": [
                    {
                        "node": "sanitize_input",
                        "response_content": "I run a pet shop"
                    },
                    {
                        "node": "extractor",
                        "response_content": '{"trigger": null, "actor": "Pet shop staff", "activity": null, "system": null, "friction": null}'
                    },
                    {
                        "node": "question_generator",
                        "response_content": "What usually starts this process?"
                    }
                ]
            },
            {
                "user_input": "We receive orders on WhatsApp",
                "expected_status": "AWAITING_CLARIFICATION",
                "expected_components": {
                    "actor": "Pet shop staff",
                    "trigger": "WhatsApp orders"
                },
                "clarification_turns": 0, # Override turn count to prevent escape hatch
                "mock_llm_responses": [
                    {
                        "node": "sanitize_input",
                        "response_content": "We receive orders on WhatsApp"
                    },
                    {
                        "node": "extractor",
                        "response_content": '{"trigger": "WhatsApp orders", "actor": "Pet shop staff", "activity": null, "system": null, "friction": null}'
                    },
                    {
                        "node": "question_generator",
                        "response_content": "What app, tool, notebook, or other place do you use to manage these orders?"
                    }
                ]
            },
            {
                "user_input": "Type them into Excel",
                "expected_status": "AWAITING_CLARIFICATION",
                "expected_components": {
                    "actor": "Pet shop staff",
                    "trigger": "WhatsApp orders",
                    "activity": "Type orders",
                    "system": "Excel"
                },
                "clarification_turns": 1, # Keep under threshold (2) to let extractor run
                "mock_llm_responses": [
                    {
                        "node": "sanitize_input",
                        "response_content": "Type them into Excel"
                    },
                    {
                        "node": "extractor",
                        "response_content": '{"trigger": "WhatsApp orders", "actor": "Pet shop staff", "activity": "Type orders", "system": "Excel", "friction": null}'
                    }
                ]
            }
        ]
    },
    {
        "name": "The Escape Hatch Fallback (User states Don't Know)",
        "mode": "OPTIMIZER",
        "motivation": "REVENUE",
        "company_context": {},
        "backstory": "",
        "expect_synthesis": False,
        "user_constraints": None,
        "expected_report_contains": [],
        "turns": [
            {
                "user_input": "I don't know the exact software name.",
                "expected_status": "AWAITING_CLARIFICATION",
                "expected_components": {
                    "trigger": "UNKNOWN",
                    "actor": "UNKNOWN",
                    "activity": "UNKNOWN",
                    "system": "UNKNOWN",
                    "friction": "UNKNOWN"
                },
                "clarification_turns": None,
                "mock_llm_responses": [
                    {
                        "node": "sanitize_input",
                        "response_content": "I don't know the exact software name."
                    }
                ]
            }
        ]
    },
    {
        "name": "The Escape Hatch Fallback (Clarification Turn limit reached)",
        "mode": "OPTIMIZER",
        "motivation": "REVENUE",
        "company_context": {},
        "backstory": "",
        "expect_synthesis": False,
        "user_constraints": None,
        "initial_turns_count": 2,
        "expected_report_contains": [],
        "turns": [
            {
                "user_input": "Checking the fleet routes",
                "expected_status": "AWAITING_CLARIFICATION",
                "expected_components": {
                    "trigger": "UNKNOWN",
                    "actor": "UNKNOWN",
                    "activity": "UNKNOWN",
                    "system": "UNKNOWN",
                    "friction": "UNKNOWN"
                },
                "clarification_turns": None,
                "mock_llm_responses": [
                    {
                        "node": "sanitize_input",
                        "response_content": "Checking the fleet routes"
                    }
                ]
            }
        ]
    },
    {
        "name": "Correction Handling & Re-Playback",
        "mode": "OPTIMIZER",
        "motivation": "REVENUE",
        "company_context": {},
        "backstory": "",
        "expect_synthesis": False,
        "user_constraints": None,
        "expected_report_contains": [],
        "turns": [
            {
                "user_input": "Incoming box triggers receiver to count items in Excel, takes 2 hours.",
                "expected_status": "AWAITING_CLARIFICATION",
                "expected_components": {
                    "trigger": "Incoming box",
                    "actor": "Receiver",
                    "activity": "Count items",
                    "system": "Excel",
                    "friction": "takes 2 hours"
                },
                "clarification_turns": None,
                "mock_llm_responses": [
                    {
                        "node": "sanitize_input",
                        "response_content": "Incoming box triggers receiver to count items in Excel, takes 2 hours."
                    },
                    {
                        "node": "extractor",
                        "response_content": '{"trigger": "Incoming box", "actor": "Receiver", "activity": "Count items", "system": "Excel", "friction": "takes 2 hours"}'
                    }
                ]
            },
            {
                "user_input": "No, we use Tally, not Excel",
                "expected_status": "AWAITING_CLARIFICATION",
                "expected_components": {
                    "trigger": "Incoming box",
                    "actor": "Receiver",
                    "activity": "Count items",
                    "system": "Tally",
                    "friction": "takes 2 hours"
                },
                "clarification_turns": None,
                "mock_llm_responses": [
                    {
                        "node": "sanitize_input",
                        "response_content": "No, we use Tally, not Excel"
                    },
                    {
                        "node": "confirm_gate",
                        "response_content": '{"is_confirmation": false, "corrections": {"trigger": null, "actor": null, "activity": null, "system": "Tally", "friction": null}}'
                    }
                ]
            }
        ]
    },
    {
        "name": "Full Workflow Execution & Synthesis",
        "mode": "OPTIMIZER",
        "motivation": "REVENUE",
        "company_context": {},
        "backstory": "",
        "expect_synthesis": True,
        "user_constraints": ["No Budget", "Strict Data Privacy"],
        "expected_report_contains": [],
        "turns": [
            {
                "user_input": "Incoming box triggers receiver to count items in Tally, takes 2 hours.",
                "expected_status": "AWAITING_CLARIFICATION",
                "expected_components": {
                    "trigger": "Incoming box",
                    "actor": "Receiver",
                    "activity": "Count items",
                    "system": "Tally",
                    "friction": "takes 2 hours"
                },
                "clarification_turns": None,
                "mock_llm_responses": [
                    {
                        "node": "sanitize_input",
                        "response_content": "Incoming box triggers receiver to count items in Tally, takes 2 hours."
                    },
                    {
                        "node": "extractor",
                        "response_content": '{"trigger": "Incoming box", "actor": "Receiver", "activity": "Count items", "system": "Tally", "friction": "takes 2 hours"}'
                    }
                ]
            },
            {
                "user_input": "Yes, correct",
                "expected_status": "COMPLETED",
                "expected_components": {
                    "trigger": "Incoming box",
                    "actor": "Receiver",
                    "activity": "Count items",
                    "system": "Tally",
                    "friction": "takes 2 hours"
                },
                "clarification_turns": None,
                "mock_llm_responses": [
                    {
                        "node": "sanitize_input",
                        "response_content": "Yes, correct"
                    },
                    {
                        "node": "confirm_gate",
                        "response_content": '{"is_confirmation": true, "corrections": {}}'
                    },
                    {
                        "node": "synthesize_report",
                        "response_content": '{"as_is_workflow": "Incoming boxes are counted and logged manually.", "friction_analysis": "Count validation takes 2 hours, delaying inventory tracking.", "technology_neutral_recommendations": "1. Tier 1 (Policy): Standardize batch sizing.\\n2. Tier 2 (SaaS): Use Tally barcode scanner.\\n3. Tier 3 (Gen AI): Not recommended here.", "roi_economics": "Saves 10 hours/week. ROI (Return on Investment: net benefit relative to cost) expected in under 2 months."}'
                    }
                ]
            }
        ]
    },
    {
        "name": "India-Specific B2C Kirana Store (WhatsApp & UPI)",
        "mode": "OPTIMIZER",
        "motivation": "REVENUE",
        "company_context": {},
        "backstory": "",
        "expect_synthesis": True,
        "user_constraints": ["Low Budget"],
        "expected_report_contains": [],
        "turns": [
            {
                "user_input": "Customers send grocery lists on WhatsApp. They pay via PhonePe and send UPI screenshots. We pack the bags and deliver them in the neighborhood.",
                "expected_status": "AWAITING_CLARIFICATION",
                "expected_components": {
                    "trigger": "WhatsApp list & UPI screenshot",
                    "actor": None,
                    "activity": "Pack and deliver",
                    "system": None,
                    "friction": None
                },
                "clarification_turns": None,
                "mock_llm_responses": [
                    {
                        "node": "sanitize_input",
                        "response_content": "Customers send grocery lists on WhatsApp. They pay via PhonePe and send UPI screenshots. We pack the bags and deliver them in the neighborhood."
                    },
                    {
                        "node": "extractor",
                        "response_content": '{"trigger": "WhatsApp list & UPI screenshot", "actor": null, "activity": "Pack and deliver", "system": null, "friction": null}'
                    },
                    {
                        "node": "question_generator",
                        "response_content": "Got it. Who on your team handles reading those WhatsApp lists?"
                    }
                ]
            },
            {
                "user_input": "The store boy packs the items, and my brother writes the UPI reference number and order total in a physical bahi-khata (ledger register). Our shop is in Koramangala.",
                "expected_status": "AWAITING_CLARIFICATION",
                "expected_components": {
                    "trigger": "WhatsApp list & UPI screenshot",
                    "actor": "Store boy & Brother",
                    "activity": "Pack and deliver",
                    "system": "Physical Bahi-khata (Ledger)",
                    "friction": "Manual reconciliation of UPI screenshots and physical ledger entries",
                    "location": "Koramangala"
                },
                "clarification_turns": None,
                "mock_llm_responses": [
                    {
                        "node": "sanitize_input",
                        "response_content": "The store boy packs the items, and my brother writes the UPI reference number and order total in a physical bahi-khata (ledger register). Our shop is in Koramangala."
                    },
                    {
                        "node": "extractor",
                        "response_content": '{"trigger": "WhatsApp list & UPI screenshot", "actor": "Store boy & Brother", "activity": "Pack and deliver", "system": "Physical Bahi-khata (Ledger)", "friction": "Manual reconciliation of UPI screenshots and physical ledger entries", "location": "Koramangala"}'
                    }
                ]
            },
            {
                "user_input": "Yes, correct",
                "expected_status": "COMPLETED",
                "expected_components": {
                    "trigger": "WhatsApp list & UPI screenshot",
                    "actor": "Store boy & Brother",
                    "activity": "Pack and deliver",
                    "system": "Physical Bahi-khata (Ledger)",
                    "friction": "Manual reconciliation of UPI screenshots and physical ledger entries",
                    "location": "Koramangala"
                },
                "clarification_turns": None,
                "mock_llm_responses": [
                    {
                        "node": "sanitize_input",
                        "response_content": "Yes, correct"
                    },
                    {
                        "node": "confirm_gate",
                        "response_content": '{"is_confirmation": true, "corrections": {}}'
                    },
                    {
                        "node": "synthesize_report",
                        "response_content": '{"as_is_workflow": "Customers send grocery lists on WhatsApp and pay via PhonePe (a digital payment application) and send UPI (Unified Payments Interface: a real-time instant payment system) screenshots. The store boy packs the items, and the brother writes the UPI reference number and order total in a physical bahi-khata (ledger register).", "friction_analysis": "Manual reconciliation of UPI (Unified Payments Interface: a real-time instant payment system) screenshots and physical ledger entries causes significant overhead and delays delivery operations.", "technology_neutral_recommendations": "1. Tier 1 (Policy): Use a business UPI (Unified Payments Interface: a real-time instant payment system) QR (Quick Response: barcode) code with a physical audio soundbox to instantly confirm payments instead of manually checking screenshots.\\n2. Tier 2 (SaaS): Migrate from physical ledger books to a simple localized SaaS (Software as a Service: web subscription software) accounting application like Khatabook.\\n3. Tier 3 (Gen AI): A custom Gen AI (Generative Artificial Intelligence: advanced text generators) solution is NOT recommended here, as simple process and SaaS (Software as a Service) shifts solve the problem.", "roi_economics": "Saves 15 hours per week of manual verification. ROI (Return on Investment: net benefit relative to cost) expected within 1 month."}'
                    }
                ]
            }
        ]
    },
    {
        "name": "Ambiguous Rambling & The 'Don't Know' Fallback",
        "mode": "OPTIMIZER",
        "motivation": "REVENUE",
        "company_context": {},
        "backstory": "",
        "expect_synthesis": True,
        "user_constraints": ["Low Budget"],
        "expected_report_contains": [],
        "turns": [
            {
                "user_input": "We waste so much time on approvals. Things just get stuck in the office for days and customers get mad.",
                "expected_status": "AWAITING_CLARIFICATION",
                "expected_components": {
                    "trigger": None,
                    "actor": None,
                    "activity": "approvals",
                    "system": None,
                    "friction": "stuck in the office for days"
                },
                "clarification_turns": None,
                "mock_llm_responses": [
                    {
                        "node": "sanitize_input",
                        "response_content": "We waste so much time on approvals. Things just get stuck in the office for days and customers get mad."
                    },
                    {
                        "node": "extractor",
                        "response_content": '{"trigger": null, "actor": null, "activity": "approvals", "system": null, "friction": "stuck in the office for days"}'
                    },
                    {
                        "node": "question_generator",
                        "response_content": "That sounds frustrating. What exactly are they trying to approve?"
                    }
                ]
            },
            {
                "user_input": "I don't know, whoever is at the desk just gets a piece of paper. It's a mess.",
                "expected_status": "AWAITING_CLARIFICATION",
                "expected_components": {
                    "trigger": None,
                    "actor": "UNKNOWN",
                    "activity": "approvals",
                    "system": None,
                    "friction": "stuck in the office for days"
                },
                "clarification_turns": 0,
                "mock_llm_responses": [
                    {
                        "node": "sanitize_input",
                        "response_content": "Whoever is at the desk just gets a piece of paper. It's a mess."
                    },
                    {
                        "node": "extractor",
                        "response_content": '{"trigger": null, "actor": "UNKNOWN", "activity": "approvals", "system": null, "friction": "stuck in the office for days"}'
                    },
                    {
                        "node": "question_generator",
                        "response_content": "Understood. What specific type of document is this paper?"
                    }
                ]
            },
            {
                "user_input": "It's a customer refund request form. They have to sign it and put it in a filing cabinet at our Rajajinagar office.",
                "expected_status": "AWAITING_CLARIFICATION",
                "expected_components": {
                    "trigger": "Customer refund request form",
                    "actor": "UNKNOWN",
                    "activity": "Sign and file refund request",
                    "system": "Physical filing cabinet",
                    "friction": "stuck in the office for days",
                    "location": "Rajajinagar"
                },
                "clarification_turns": 0,
                "mock_llm_responses": [
                    {
                        "node": "sanitize_input",
                        "response_content": "It's a customer refund request form. They have to sign it and put it in a filing cabinet at our Rajajinagar office."
                    },
                    {
                        "node": "extractor",
                        "response_content": '{"trigger": "Customer refund request form", "actor": "UNKNOWN", "activity": "Sign and file refund request", "system": "Physical filing cabinet", "friction": "stuck in the office for days", "location": "Rajajinagar"}'
                    }
                ]
            },
            {
                "user_input": "Yes, correct",
                "expected_status": "COMPLETED",
                "expected_components": {
                    "trigger": "Customer refund request form",
                    "actor": "UNKNOWN",
                    "activity": "Sign and file refund request",
                    "system": "Physical filing cabinet",
                    "friction": "stuck in the office for days",
                    "location": "Rajajinagar"
                },
                "clarification_turns": None,
                "mock_llm_responses": [
                    {
                        "node": "sanitize_input",
                        "response_content": "Yes, correct"
                    },
                    {
                        "node": "confirm_gate",
                        "response_content": '{"is_confirmation": true, "corrections": {}}'
                    },
                    {
                        "node": "synthesize_report",
                        "response_content": '{"as_is_workflow": "Customer refund request form paper documents arrive at the office, where they are signed by an UNKNOWN (unidentified role) actor and stored in a physical filing cabinet.", "friction_analysis": "The process suffers from a severe vulnerability due to Lack of Clear Ownership, as an UNKNOWN (unidentified role) actor handles approvals. Documents get stuck in the office for days, causing customer dissatisfaction.", "technology_neutral_recommendations": "1. Tier 1 (Policy): Assign clear ownership and roles for approving refund requests.\\n2. Tier 2 (SaaS): Adopt a standard ticketing SaaS (Software as a Service: online subscription tool) to log and route refund approvals digital workflows.\\n3. Tier 3 (Gen AI): A custom Gen AI (Generative Artificial Intelligence: advanced reasoning model) solution is NOT recommended here, as establishing clear policy ownership and digital ticketing solves the issue.", "roi_economics": "Reduces turnaround time from days to hours. ROI (Return on Investment: net benefit relative to cost) is immediate since Tier 1 policy shift is zero cost."}'
                    }
                ]
            }
        ]
    },
    {
        "name": "Backstory Clinic Appointment Follow-Up",
        "mode": "OPTIMIZER",
        "motivation": "REVENUE",
        "company_context": {
            "name": "Maya Family Clinic",
            "industry": "Neighborhood healthcare clinic",
            "core_tools": "Phone calls, paper diary, WhatsApp, Google Calendar"
        },
        "backstory": (
            "Maya Family Clinic is a six-person neighborhood clinic in Indiranagar. "
            "The receptionist handles walk-ins, phone appointments, lab-result follow-ups, "
            "and doctor schedule changes from a front desk notebook. Missed reminders cause "
            "patients to call repeatedly and leave empty slots in the evening schedule."
        ),
        "expect_synthesis": True,
        "user_constraints": ["Low Budget", "No new complex software"],
        "expected_report_contains": ["shared calendar", "reminder", "no-show"],
        "turns": [
            {
                "user_input": "Appointments are a headache and patients keep calling again.",
                "expected_status": "AWAITING_CLARIFICATION",
                "expected_components": {
                    "trigger": None,
                    "actor": None,
                    "activity": "Manage patient appointments and follow-ups",
                    "system": None,
                    "friction": "patients keep calling again",
                    "location": None
                },
                "clarification_turns": None,
                "mock_llm_responses": [
                    {
                        "node": "sanitize_input",
                        "response_content": "Appointments are a headache and patients keep calling again."
                    },
                    {
                        "node": "extractor",
                        "response_content": '{"trigger": null, "actor": null, "activity": "Manage patient appointments and follow-ups", "system": null, "friction": "patients keep calling again", "location": null}'
                    },
                    {
                        "node": "question_generator",
                        "response_content": "Who handles appointment changes today?"
                    }
                ]
            },
            {
                "user_input": "Our receptionist gets phone calls and WhatsApp messages, writes appointments in a paper diary, then copies some confirmed visits into Google Calendar. We are in Indiranagar.",
                "expected_status": "AWAITING_CLARIFICATION",
                "expected_components": {
                    "trigger": "Phone calls and WhatsApp appointment messages",
                    "actor": "Receptionist",
                    "activity": "Write appointments and copy confirmed visits",
                    "system": "Paper diary and Google Calendar",
                    "friction": "Double entry causes missed reminders and repeat patient calls",
                    "location": "Indiranagar"
                },
                "clarification_turns": None,
                "mock_llm_responses": [
                    {
                        "node": "sanitize_input",
                        "response_content": "Our receptionist gets phone calls and WhatsApp messages, writes appointments in a paper diary, then copies some confirmed visits into Google Calendar. We are in Indiranagar."
                    },
                    {
                        "node": "extractor",
                        "response_content": '{"trigger": "Phone calls and WhatsApp appointment messages", "actor": "Receptionist", "activity": "Write appointments and copy confirmed visits", "system": "Paper diary and Google Calendar", "friction": "Double entry causes missed reminders and repeat patient calls", "location": "Indiranagar"}'
                    }
                ]
            },
            {
                "user_input": "Yes, correct",
                "expected_status": "COMPLETED",
                "expected_components": {
                    "trigger": "Phone calls and WhatsApp appointment messages",
                    "actor": "Receptionist",
                    "activity": "Write appointments and copy confirmed visits",
                    "system": "Paper diary and Google Calendar",
                    "friction": "Double entry causes missed reminders and repeat patient calls",
                    "location": "Indiranagar"
                },
                "clarification_turns": None,
                "mock_llm_responses": [
                    {
                        "node": "sanitize_input",
                        "response_content": "Yes, correct"
                    },
                    {
                        "node": "confirm_gate",
                        "response_content": '{"is_confirmation": true, "corrections": {}}'
                    },
                    {
                        "node": "synthesize_report",
                        "response_content": '{"as_is_workflow": "Patients call or send WhatsApp messages. The receptionist writes appointments in a paper diary, then copies some confirmed visits into Google Calendar.", "friction_analysis": "The same appointment is handled twice, so reminders are missed and patients call again. Empty slots can turn into no-show losses.", "technology_neutral_recommendations": "1. Tier 1 (Policy): Make Google Calendar the shared calendar of record and stop writing confirmed visits in two places.\\n2. Tier 2 (SaaS): Use WhatsApp reminder templates or a low-cost appointment reminder tool for next-day confirmations.\\n3. Tier 3 (Gen AI): Not recommended now because the main problem is simple schedule discipline and reminder consistency.", "roi_economics": "Reducing two no-show appointments per week can recover meaningful revenue. ROI (Return on Investment: return compared with cost, like checking whether a repair saves more money than it costs) should be visible within the first month."}'
                    }
                ]
            }
        ]
    },
    {
        "name": "Backstory Repair Shop Status Calls",
        "mode": "OPTIMIZER",
        "motivation": "REVENUE",
        "company_context": {
            "name": "Ravi Auto Works",
            "industry": "Two-wheeler repair shop",
            "core_tools": "Paper job cards, WhatsApp, wall board"
        },
        "backstory": (
            "Ravi Auto Works repairs 25 to 35 scooters and motorcycles per day. "
            "A service advisor writes paper job cards, mechanics update him verbally, "
            "and customers call every few hours because they cannot see whether a vehicle "
            "is waiting for parts, under repair, ready for pickup, or delayed."
        ),
        "expect_synthesis": True,
        "user_constraints": ["Low Budget", "Owner wants staff to adopt it in one week"],
        "expected_report_contains": ["status board", "job stages", "WhatsApp"],
        "turns": [
            {
                "user_input": "Customers keep calling about status and the front desk gets overwhelmed.",
                "expected_status": "AWAITING_CLARIFICATION",
                "expected_components": {
                    "trigger": None,
                    "actor": "Front desk",
                    "activity": "Answer customer status calls",
                    "system": None,
                    "friction": "front desk gets overwhelmed",
                    "location": None
                },
                "clarification_turns": None,
                "mock_llm_responses": [
                    {
                        "node": "sanitize_input",
                        "response_content": "Customers keep calling about status and the front desk gets overwhelmed."
                    },
                    {
                        "node": "extractor",
                        "response_content": '{"trigger": null, "actor": "Front desk", "activity": "Answer customer status calls", "system": null, "friction": "front desk gets overwhelmed", "location": null}'
                    },
                    {
                        "node": "question_generator",
                        "response_content": "How does a repair job start today?"
                    }
                ]
            },
            {
                "user_input": "The service advisor writes a paper job card when a bike comes in near Jayanagar. Mechanics just tell him verbally if parts are needed or if pickup is ready, and he replies on WhatsApp when he remembers.",
                "expected_status": "AWAITING_CLARIFICATION",
                "expected_components": {
                    "trigger": "Bike arrives for repair",
                    "actor": "Service advisor and mechanics",
                    "activity": "Write job cards and share repair status",
                    "system": "Paper job cards and WhatsApp",
                    "friction": "Verbal mechanic updates are forgotten before customer follow-up",
                    "location": "Jayanagar"
                },
                "clarification_turns": None,
                "mock_llm_responses": [
                    {
                        "node": "sanitize_input",
                        "response_content": "The service advisor writes a paper job card when a bike comes in near Jayanagar. Mechanics just tell him verbally if parts are needed or if pickup is ready, and he replies on WhatsApp when he remembers."
                    },
                    {
                        "node": "extractor",
                        "response_content": '{"trigger": "Bike arrives for repair", "actor": "Service advisor and mechanics", "activity": "Write job cards and share repair status", "system": "Paper job cards and WhatsApp", "friction": "Verbal mechanic updates are forgotten before customer follow-up", "location": "Jayanagar"}'
                    }
                ]
            },
            {
                "user_input": "Yes, correct",
                "expected_status": "COMPLETED",
                "expected_components": {
                    "trigger": "Bike arrives for repair",
                    "actor": "Service advisor and mechanics",
                    "activity": "Write job cards and share repair status",
                    "system": "Paper job cards and WhatsApp",
                    "friction": "Verbal mechanic updates are forgotten before customer follow-up",
                    "location": "Jayanagar"
                },
                "clarification_turns": None,
                "mock_llm_responses": [
                    {
                        "node": "sanitize_input",
                        "response_content": "Yes, correct"
                    },
                    {
                        "node": "confirm_gate",
                        "response_content": '{"is_confirmation": true, "corrections": {}}'
                    },
                    {
                        "node": "synthesize_report",
                        "response_content": '{"as_is_workflow": "A bike arrives, the service advisor creates a paper job card, mechanics share updates verbally, and WhatsApp replies are sent when someone remembers.", "friction_analysis": "The status lives in staff memory, so customers call repeatedly and the front desk becomes the memory system.", "technology_neutral_recommendations": "1. Tier 1 (Policy): Create four visible job stages on a status board: received, waiting for parts, under repair, ready for pickup. Mechanics must move the card before starting the next bike.\\n2. Tier 2 (SaaS): Use saved WhatsApp templates for each job stage so the advisor can send consistent updates quickly.\\n3. Tier 3 (Gen AI): Not recommended until the shop has reliable job-stage data.", "roi_economics": "If the status board prevents 20 repeat calls per day, the advisor gains back several hours each week. ROI (Return on Investment: return compared with cost, like seeing whether a tool pays for itself) is likely immediate because the first step uses existing paper cards."}'
                    }
                ]
            }
        ]
    },
    {
        "name": "Backstory Wholesale Distributor Billing Delay",
        "mode": "OPTIMIZER",
        "motivation": "REVENUE",
        "company_context": {
            "name": "Northstar Electrical Distributors",
            "industry": "Wholesale electrical parts distributor",
            "core_tools": "Excel, Tally, email, warehouse stock register"
        },
        "backstory": (
            "Northstar Electrical Distributors sells switches, wiring, and fittings to "
            "contractors. Sales staff receive purchase orders by email, warehouse staff "
            "check stock in a register, and accounts retypes invoice details into Tally. "
            "Dispatch is often ready before billing, so trucks wait at the loading bay."
        ),
        "expect_synthesis": True,
        "user_constraints": ["Keep Tally", "Do not disrupt warehouse staff"],
        "expected_report_contains": ["import-ready", "Tally", "stock check"],
        "turns": [
            {
                "user_input": "Billing takes too long and dispatch keeps waiting.",
                "expected_status": "AWAITING_CLARIFICATION",
                "expected_components": {
                    "trigger": None,
                    "actor": None,
                    "activity": "Billing and dispatch coordination",
                    "system": None,
                    "friction": "dispatch keeps waiting",
                    "location": None
                },
                "clarification_turns": None,
                "mock_llm_responses": [
                    {
                        "node": "sanitize_input",
                        "response_content": "Billing takes too long and dispatch keeps waiting."
                    },
                    {
                        "node": "extractor",
                        "response_content": '{"trigger": null, "actor": null, "activity": "Billing and dispatch coordination", "system": null, "friction": "dispatch keeps waiting", "location": null}'
                    },
                    {
                        "node": "question_generator",
                        "response_content": "What usually starts a bill today?"
                    }
                ]
            },
            {
                "user_input": "Sales gets contractor purchase orders by email, checks stock with the warehouse register in Peenya, then accounts copies line items from Excel into Tally before the truck can leave.",
                "expected_status": "AWAITING_CLARIFICATION",
                "expected_components": {
                    "trigger": "Contractor purchase order by email",
                    "actor": "Sales, warehouse, and accounts",
                    "activity": "Check stock and create invoice before dispatch",
                    "system": "Email, Excel, warehouse register, and Tally",
                    "friction": "Accounts retypes Excel line items into Tally while dispatch waits",
                    "location": "Peenya"
                },
                "clarification_turns": None,
                "mock_llm_responses": [
                    {
                        "node": "sanitize_input",
                        "response_content": "Sales gets contractor purchase orders by email, checks stock with the warehouse register in Peenya, then accounts copies line items from Excel into Tally before the truck can leave."
                    },
                    {
                        "node": "extractor",
                        "response_content": '{"trigger": "Contractor purchase order by email", "actor": "Sales, warehouse, and accounts", "activity": "Check stock and create invoice before dispatch", "system": "Email, Excel, warehouse register, and Tally", "friction": "Accounts retypes Excel line items into Tally while dispatch waits", "location": "Peenya"}'
                    }
                ]
            },
            {
                "user_input": "Yes, correct",
                "expected_status": "COMPLETED",
                "expected_components": {
                    "trigger": "Contractor purchase order by email",
                    "actor": "Sales, warehouse, and accounts",
                    "activity": "Check stock and create invoice before dispatch",
                    "system": "Email, Excel, warehouse register, and Tally",
                    "friction": "Accounts retypes Excel line items into Tally while dispatch waits",
                    "location": "Peenya"
                },
                "clarification_turns": None,
                "mock_llm_responses": [
                    {
                        "node": "sanitize_input",
                        "response_content": "Yes, correct"
                    },
                    {
                        "node": "confirm_gate",
                        "response_content": '{"is_confirmation": true, "corrections": {}}'
                    },
                    {
                        "node": "synthesize_report",
                        "response_content": '{"as_is_workflow": "Contractor purchase orders arrive by email. Sales checks stock with the warehouse register, prepares Excel line items, and accounts retypes those details into Tally before dispatch.", "friction_analysis": "The stock check and invoice creation are split across people and files. Dispatch waits because accounts repeats data entry that sales already completed.", "technology_neutral_recommendations": "1. Tier 1 (Policy): Use one standard order sheet with item code, quantity, stock check, and approval columns before dispatch starts loading.\\n2. Tier 2 (SaaS): Make the Excel order sheet import-ready for Tally so accounts reviews instead of retyping.\\n3. Tier 3 (Gen AI): Not recommended here because structured order and stock data should be fixed before any AI layer is useful.", "roi_economics": "If import-ready Tally entries save 10 minutes per order across 30 orders per day, dispatch delays should fall quickly. ROI (Return on Investment: return compared with cost, like comparing saved fuel and staff time against setup effort) should be measurable within one billing cycle."}'
                    }
                ]
            }
        ]
    }
]
