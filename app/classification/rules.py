import logging

logger = logging.getLogger(__name__)

CATEGORY_RULES = {
    "Salary": ["salary", "payroll", "sal ", "stipend", "remuneration"],
    "Investment / Interest": ["interest", "int.pd", "int pd", "dividend", "mutual fund", "zerodha", "groww", "kuvera", "upstox", "demat", "bse", "nse", "term deposit"],
    "Loan EMI": ["emi", "loan", "bajaj finance", "home loan", "personal loan", "hfl"],
    "Credit Card": ["credit card", "cc bill", "cred", "card payment"],
    "Utilities & Bills": ["electricity", "bescom", "billdesk", "airtel", "jio", "vodafone", "vi ", "recharge", "broadband", "water bill", "gas", "cesc", "tneb", "dth"],
    "Healthcare": ["hospital", "medical", "pharmacy", "apollo", "medplus", "clinic", "health", "dr.", "diagnostic", "1mg"],
    "Travel & Transport": ["uber", "ola", "irctc", "makemytrip", "flight", "railway", "transport", "bus", "metro", "roppen", "rapido", "indigo", "air india", "redbus", "goibibo", "fuel", "petrol", "hpcl", "bpcl", "ioc"],
    "Food": ["swiggy", "zomato", "restaurant", "dominos", "kfc", "mcdonalds", "cafe", "hotel", "food", "dine", "pizza", "vada paav", "burger", "bakery", "eats", "tea", "coffee"],
    "Shopping": ["amazon", "flipkart", "myntra", "ajio", "retail", "store", "mart", "tanishq", "reliancedigital", "croma", "nykaa", "supermarket", "groceries", "blinkit", "zepto", "instamart"],
    "ATM Withdrawal": ["atm", "cash withdrawal", "nfs", "cash wdl", "atm wdl", "cwdr"],
    "Charges & Fees": ["charge", "charges", "fee", "penalty", "sms charge", "min bal", "gst", "cgst", "sgst"],
    "Transfer": ["imps", "neft", "rtgs", "fund transfer", "trf", "transfer"],
    "Entertainment": ["netflix", "prime", "hotstar", "spotify", "cinema", "pvr", "inox", "bookmyshow", "youtube"],
    "UPI": ["upi", "vpa", "/upi/"]
}

RULE_PRIORITY = [
    "Salary",
    "Investment / Interest",
    "Loan EMI",
    "Credit Card",
    "Utilities & Bills",
    "Healthcare",
    "Travel & Transport",
    "Food",
    "Shopping",
    "Entertainment",
    "ATM Withdrawal",
    "Charges & Fees",
    "Transfer",
    "UPI"
]


def classify_transaction_rule_based(description: str) -> str:
    """
    Classifies a transaction description using keyword-based heuristics.
    Returns standard financial category name or 'Others' if unmatched.
    """
    try:
        if not description or not isinstance(description, str):
            return "Others"

        desc = description.lower()

        # Check by priority first
        for category in RULE_PRIORITY:
            keywords = CATEGORY_RULES.get(category, [])
            for keyword in keywords:
                if keyword in desc:
                    return category

        # Check any remaining categories
        for category, keywords in CATEGORY_RULES.items():
            if category not in RULE_PRIORITY:
                for keyword in keywords:
                    if keyword in desc:
                        return category

        return "Others"
    except Exception as err:
        logger.error(f"Error classifying transaction '{description}': {err}")
        return "Others"

