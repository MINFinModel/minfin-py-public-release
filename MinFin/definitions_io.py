"""Definition row models and loaders (from Definitions sheet columns)."""


class BaseDefinition:
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    def __repr__(self):
        return f"{self.__class__.__name__}(name='{self.name}', description='{self.description}')"


class ParameterConstraint(BaseDefinition):
    pass


class FinancingBaseline(BaseDefinition):
    pass


class FundingBaseline(BaseDefinition):
    pass


class Scenario(BaseDefinition):
    pass


class Currency:
    def __init__(self, code: str, currency: str):
        self.code = code
        self.currency = currency

    def __repr__(self):
        return f"Currency(code='{self.code}', currency='{self.currency}')"


class Technology:
    def __init__(self, name: str, technology: str, description: str, classification: str):
        self.name = name
        self.description = description
        self.classification = classification
        self.technology = technology

    def __repr__(self):
        return (
            f"Technology(name='{self.name}', tech='{self.technology}', "
            f"description='{self.description}', classification='{self.classification}')"
        )


def load_definitions_from_dataframe(df, cls):
    return [cls(row["Name"], row["Description"]) for _, row in df.iterrows()]


def load_currencies_from_dataframe(df):
    return [Currency(row["Code"], row["Currency"]) for _, row in df.iterrows()]


def load_technologies_from_dataframe(df):
    return [
        Technology(row["Name"], row["Technology"], row["Description"], row["Classification"])
        for _, row in df.iterrows()
    ]
