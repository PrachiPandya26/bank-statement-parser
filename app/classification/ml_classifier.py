import logging
from typing import Optional

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

logger = logging.getLogger(__name__)


class MLClassifier:
    """
    Traditional Machine Learning classifier for transaction descriptions.
    Uses TF-IDF + Logistic Regression trained in-memory.
    """
    def __init__(self):
        self.pipeline: Optional[Pipeline] = None
        try:
            self.pipeline = self._train_mock_model()
        except Exception as err:
            logger.error(f"Failed to initialize ML classifier: {err}")
            self.pipeline = None

    def _train_mock_model(self) -> Pipeline:
        """
        Trains a lightweight non-LLM classifier on typical financial statement vocabulary.
        """
        try:
            data = {
                "description": [
                    "UPI SWIGGY BANGALORE", "ZOMATO RESTAURANT ORDER", "DOMINOS PIZZA DINING",
                    "NEFT SALARY ACME CORP", "PAYROLL DIRECT DEPOSIT", "MONTHLY SALARY TRANSFER",
                    "AMAZON INDIA SHOPPING", "FLIPKART INTERNET PURCHASE", "MYNTRA DESIGNS RETAIL",
                    "CASH WITHDRAWAL ATM", "NFS CASH WDL", "ATM TXN DEBIT",
                    "NETFLIX SUBSCRIPTION", "SPOTIFY PREMIUM", "PVR CINEMAS TICKET",
                    "LOAN EMI HDFC", "BAJAJ FINANCE EMI LOAN", "AUTO LOAN PAYMENT",
                    "INTEREST PAID SAVINGS", "TERM DEPOSIT INT.PD", "DIVIDEND CREDIT",
                    "AIRTEL MOBILE RECHARGE", "ELECTRICITY BILL PAYMENT", "BESCOM UTILITY BILL",
                    "APOLLO PHARMACY MEDICAL", "HOSPITAL CLINIC HEALTHCARE",
                    "UBER TRIP RIDE", "OLA CABS TRANSPORT", "IRCTC TRAIN TICKET"
                ],
                "category": [
                    "Food", "Food", "Food",
                    "Salary", "Salary", "Salary",
                    "Shopping", "Shopping", "Shopping",
                    "ATM Withdrawal", "ATM Withdrawal", "ATM Withdrawal",
                    "Entertainment", "Entertainment", "Entertainment",
                    "Loan EMI", "Loan EMI", "Loan EMI",
                    "Investment / Interest", "Investment / Interest", "Investment / Interest",
                    "Utilities & Bills", "Utilities & Bills", "Utilities & Bills",
                    "Healthcare", "Healthcare",
                    "Travel & Transport", "Travel & Transport", "Travel & Transport"
                ]
            }
            df = pd.DataFrame(data)

            pipeline = Pipeline([
                ("tfidf", TfidfVectorizer(ngram_range=(1, 2))),
                ("classifier", LogisticRegression(max_iter=200, random_state=42))
            ])
            pipeline.fit(df["description"], df["category"])
            logger.info("ML classification pipeline trained successfully.")
            return pipeline
        except Exception as err:
            logger.error(f"Error training ML model: {err}")
            raise

    def predict(self, description: str) -> str:
        """
        Predicts transaction category. Returns 'Others' if model is not available,
        input is empty, or no training vocabulary is present in description.
        """
        try:
            if not self.pipeline or not description or not isinstance(description, str):
                return "Others"

            tfidf = self.pipeline.named_steps.get("tfidf")
            if tfidf:
                vec = tfidf.transform([description])
                if vec.nnz == 0:
                    return "Others"

            prediction = self.pipeline.predict([description])[0]
            return str(prediction)
        except Exception as err:
            logger.error(f"Error predicting category for '{description}': {err}")
            return "Others"


try:
    classifier_instance = MLClassifier()
except Exception as init_err:
    logger.error(f"Failed to create MLClassifier instance: {init_err}")
    classifier_instance = None


def classify_transaction_ml(description: str) -> str:
    """
    Wrapper function to classify transaction using the ML model instance.
    """
    try:
        if classifier_instance:
            return classifier_instance.predict(description)
        return "Others"
    except Exception as err:
        logger.error(f"Error in classify_transaction_ml: {err}")
        return "Others"


# Alias for backward compatibility
MLTransactionClassifier = MLClassifier

