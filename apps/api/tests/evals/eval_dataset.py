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
    turns: List[Turn]
    expect_synthesis: bool
    user_constraints: Optional[List[str]]
    initial_turns_count: Optional[int]

GOLDEN_SCENARIOS: List[EvalScenario] = [
    {
        "name": "Short Starter Chip Clarification",
        "mode": "OPTIMIZER",
        "motivation": "EDUCATION",
        "expect_synthesis": False,
        "user_constraints": None,
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
                        "response_content": "What system or software do you use, and what is the primary friction?"
                    }
                ]
            }
        ]
    },
    {
        "name": "Messy Multi-Turn Intake Accumulation",
        "mode": "OPTIMIZER",
        "motivation": "REVENUE",
        "expect_synthesis": False,
        "user_constraints": None,
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
                        "response_content": "What event starts your process, and what software do you use?"
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
                        "response_content": "What software or tools do you use to manage these orders, and what activities do you perform?"
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
        "expect_synthesis": False,
        "user_constraints": None,
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
        "expect_synthesis": False,
        "user_constraints": None,
        "initial_turns_count": 2,
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
        "expect_synthesis": False,
        "user_constraints": None,
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
        "expect_synthesis": True,
        "user_constraints": ["No Budget", "Strict Data Privacy"],
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
        "expect_synthesis": True,
        "user_constraints": ["Low Budget"],
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
                        "response_content": "Got it. Who on your team handles reading those WhatsApp lists, and where do you keep track of the payments and orders?"
                    }
                ]
            },
            {
                "user_input": "The store boy packs the items, and my brother writes the UPI reference number and order total in a physical bahi-khata (ledger register).",
                "expected_status": "AWAITING_CLARIFICATION",
                "expected_components": {
                    "trigger": "WhatsApp list & UPI screenshot",
                    "actor": "Store boy & Brother",
                    "activity": "Pack and deliver",
                    "system": "Physical Bahi-khata (Ledger)",
                    "friction": "Manual reconciliation of UPI screenshots and physical ledger entries"
                },
                "clarification_turns": None,
                "mock_llm_responses": [
                    {
                        "node": "sanitize_input",
                        "response_content": "The store boy packs the items, and my brother writes the UPI reference number and order total in a physical bahi-khata (ledger register)."
                    },
                    {
                        "node": "extractor",
                        "response_content": '{"trigger": "WhatsApp list & UPI screenshot", "actor": "Store boy & Brother", "activity": "Pack and deliver", "system": "Physical Bahi-khata (Ledger)", "friction": "Manual reconciliation of UPI screenshots and physical ledger entries"}'
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
                    "friction": "Manual reconciliation of UPI screenshots and physical ledger entries"
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
        "expect_synthesis": True,
        "user_constraints": ["Low Budget"],
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
                        "response_content": "That sounds frustrating. What exactly are they trying to approve, and how does that request arrive at the office?"
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
                        "response_content": "Understood. What specific type of document is this paper, and what are they supposed to do with it once they get it?"
                    }
                ]
            },
            {
                "user_input": "It's a customer refund request form. They have to sign it and put it in a filing cabinet.",
                "expected_status": "AWAITING_CLARIFICATION",
                "expected_components": {
                    "trigger": "Customer refund request form",
                    "actor": "UNKNOWN",
                    "activity": "Sign and file refund request",
                    "system": "Physical filing cabinet",
                    "friction": "stuck in the office for days"
                },
                "clarification_turns": 0,
                "mock_llm_responses": [
                    {
                        "node": "sanitize_input",
                        "response_content": "It's a customer refund request form. They have to sign it and put it in a filing cabinet."
                    },
                    {
                        "node": "extractor",
                        "response_content": '{"trigger": "Customer refund request form", "actor": "UNKNOWN", "activity": "Sign and file refund request", "system": "Physical filing cabinet", "friction": "stuck in the office for days"}'
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
                    "friction": "stuck in the office for days"
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
    }
]
