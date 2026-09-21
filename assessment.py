from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import os
import json
import prompts
from textwrap import dedent
import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv

#Enums used for choices
class EquipmentProvider(str, Enum):
    CLIENT = "client"
    WORKER = "worker"
    MIXED = "mixed"

class SubPaymentEnum(str, Enum):
    CLIENT = "client"
    WORKER = "worker"
    UNSPECIFIED = "unspecified"

class PaidForTimeOrCompletionEnum(str, Enum):
    TIME = "time"
    COMPLETION = "completion"
    BOTH = "both"

#Data class for structure of assessment
@dataclass
class Engagement:
    engagement_id: str
    #Gate 1 (personal service)
    substitution_clause: bool
    substitution_attempted: str
    substitute_payment: SubPaymentEnum
    #Gate 2 (control)
    decides_what_work_and_what_order: str
    decides_how_work_performed: str
    hours_and_location_set: str
    report_to_a_manager: str
    #Condition 3
    #In business on own account
    clients_last_12_months: int
    own_trading_name: bool
    own_insurance: bool
    own_vat: bool
    #Financial Risk
    defective_work_corrected: str
    loss_on_engagement: str
    #Equipment
    who_provide_equipment: EquipmentProvider
    #Integration
    presented_as_part_of_organisation: str
    staff_benefits_training_management: str
    #Exclusivity and duration
    total_engagement_length: int
    extension_count: int
    exclusivity_clause: bool
    practical_bar: str
    #Payment
    paid_for_time_or_completion: PaidForTimeOrCompletionEnum
    substitution_fettered: Optional[bool] = None

#To load in external csv files
def load_engagements(path):
    df = pd.read_csv(path)
    engagement = []

    #In the for loop _ is calling the row number each time and then row is the information
    #What Df is - is the copy of the file contents uploaded loaded into memory  df.iloc[0] pulls out one row. row["engagement_id"] pulls one cell from that row.
    #What iterrows() does - walks through df and hands back a row at a time (row) but also hands back a row number each time (_) 
    for _ , row in df.iterrows():
        e = Engagement(
        engagement_id=row["engagement_id"],
        substitution_clause=row["substitution_clause"],
        substitution_attempted=row["substitution_attempted"],
        substitute_payment=SubPaymentEnum(row["substitute_payment"]),
        decides_what_work_and_what_order=row["decides_what_work_and_what_order"],
        decides_how_work_performed=row["decides_how_work_performed"],
        hours_and_location_set=row["hours_and_location_set"],
        report_to_a_manager=row["report_to_a_manager"],
        clients_last_12_months=row["clients_last_12_months"],
        own_trading_name=row["own_trading_name"],
        own_insurance=row["own_insurance"],
        own_vat=row["own_vat"],
        defective_work_corrected=row["defective_work_corrected"],
        loss_on_engagement=row["loss_on_engagement"],
        who_provide_equipment=EquipmentProvider(row["who_provide_equipment"]),
        presented_as_part_of_organisation=row["presented_as_part_of_organisation"],
        staff_benefits_training_management=row["staff_benefits_training_management"],
        total_engagement_length=row["total_engagement_length"],
        extension_count=row["extension_count"],
        exclusivity_clause=row["exclusivity_clause"],
        practical_bar=row["practical_bar"],
        paid_for_time_or_completion=PaidForTimeOrCompletionEnum(row["paid_for_time_or_completion"]),
        substitution_fettered=None if pd.isna(row["substitution_fettered"]) else row["substitution_fettered"],)
        engagement.append(e)
    return engagement


#Gate Outcome Class
class GateOutcome(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    UNCLEAR = "unclear"

#GateResult class
@dataclass
class GateResult:
    outcome: GateOutcome
    reasoning: str
    evidence: str
    contradiction: Optional[str] = None

#Factor Strength class
class FactorStrength(str, Enum):
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"

#Factor Direction class
class FactorDirection(str, Enum):
    EMPLOYMENT = "employment"
    SELFEMPLOYMENT = "self employment"
    NEUTRAL = "neutral"

#Factor Result
@dataclass
class FactorResult:
    factor: str
    strength: FactorStrength
    direction: FactorDirection
    evidence: str
    sufficiency: str

#Deterministic function for equipment provider question no api call needed, simply uses multiple choice ENUM to decide factor result
def assess_equipment(engagement):
    if engagement.who_provide_equipment==EquipmentProvider.CLIENT:
        return FactorResult(
            factor = "equipment",
            direction = FactorDirection.EMPLOYMENT,
            strength = FactorStrength.MODERATE,
            evidence="Equipment provided by the client",
            sufficiency="assessable",
        )
    if engagement.who_provide_equipment==EquipmentProvider.WORKER:
        return FactorResult(
            factor = "equipment",
            direction = FactorDirection.SELFEMPLOYMENT,
            strength = FactorStrength.MODERATE,
            evidence="Equipment provided by the worker",
            sufficiency="assessable",
        )
    if engagement.who_provide_equipment==EquipmentProvider.MIXED:
        return FactorResult(
                factor = "equipment",
                direction = FactorDirection.NEUTRAL,
                strength = FactorStrength.MODERATE,
                evidence="Equipment provided by both client and worker",
                sufficiency="assessable",
            )

#Deterministic function for payment related questions no api call needed, simply uses multiple choice ENUM to decide factor result
def payment(engagement):
    if engagement.paid_for_time_or_completion == PaidForTimeOrCompletionEnum.TIME:
        return FactorResult(
            factor = "payment",
            direction = FactorDirection.EMPLOYMENT,
            strength = FactorStrength.MODERATE,
            evidence="Paid per time, in line with normal employment",
            sufficiency="assessable",
        )
    if engagement.paid_for_time_or_completion == PaidForTimeOrCompletionEnum.COMPLETION:
        return FactorResult(
            factor = "payment",
            direction = FactorDirection.SELFEMPLOYMENT,
            strength = FactorStrength.MODERATE,
            evidence="Paid per completion, not in line with normal employment practices",
            sufficiency="assessable",
        )
    if engagement.paid_for_time_or_completion == PaidForTimeOrCompletionEnum.BOTH:
        return FactorResult(
            factor = "payment",
            direction = FactorDirection.SELFEMPLOYMENT,
            strength = FactorStrength.WEAK,
            evidence="Paid per time and completion, not in line with normal employment practices",
            sufficiency="assessable",
        )

#Deterministic function for in business on own account questions no api call needed, simply uses int value to decide factor result
def in_business_on_own_account(engagement):
    indicators = 0 
    clients = ""
    trading = ""
    insurance = ""
    vat = ""
    if engagement.clients_last_12_months <= 3:
        indicators += 0
        clients = "Equal to or less than 3 clients in last 12 months"
    if engagement.clients_last_12_months > 3:
        indicators += 1
        clients = "Greater than 3 clients in last 12 months"
    if engagement.own_trading_name == True:
        indicators += 1
        trading = "Worker does have own trading name" 
    if engagement.own_trading_name == False:
        indicators += 0
        trading = "Worker does not have own trading name" 
    if engagement.own_insurance == True:
        indicators += 1
        insurance = "Worker has own insurance"
    if engagement.own_insurance == False:
        indicators += 0
        insurance = "Worker does not have own insurance"
    if engagement.own_vat == True:
        indicators += 1
        vat = "Worker has own VAT"
    if engagement.own_vat == False:
        indicators += 0 
        vat = "Worker does not have own VAT"
    
    if indicators == 0:
        return FactorResult(
            factor = "in business on own account",
            direction = FactorDirection.EMPLOYMENT,
            strength = FactorStrength.MODERATE,
            evidence=f"{clients}, {trading}, {insurance}, {vat} ",
            sufficiency="assessable",
        )
    if indicators == 1:
        return FactorResult(
            factor = "in business on own account",
            direction = FactorDirection.EMPLOYMENT,
            strength = FactorStrength.WEAK,
            evidence=f"{clients}, {trading}, {insurance}, {vat} ",
            sufficiency="assessable",
        )
    if indicators == 2:
        return FactorResult(
            factor = "in business on own account",
            direction = FactorDirection.SELFEMPLOYMENT,
            strength = FactorStrength.WEAK,
            evidence=f"{clients}, {trading}, {insurance}, {vat} ",
            sufficiency="assessable",
        )
    if indicators > 2:
        return FactorResult(
            factor = "in business on own account",
            direction = FactorDirection.SELFEMPLOYMENT,
            strength = FactorStrength.STRONG,
            evidence=f"{clients}, {trading}, {insurance}, {vat} ",
            sufficiency="assessable",
        )


#Deterministic function for exclusivity and duration questions no api call needed, simply uses int value to decide factor result
def exclusivity_and_duration(engagement):
    indicators = 0
    engagement_length = ""
    extension = ""
    exclusivity = ""
    if engagement.total_engagement_length > 18:
        indicators +=1
        engagement_length = "total engagement length greater than 18 months"
    else:
        indicators +=0
        engagement_length = "total engagement length less than 18 months"
    if engagement.extension_count > 2:
        indicators += 1
        extension = "total extension count greater than twice"
    else:
        indicators += 0
        extension = "total extension count less than twice"
    if engagement.exclusivity_clause == True:
        indicators += 2
        exclusivity = "exclusivity clause present in contract"
    else:
        indicators +=0
        exclusivity = "exclusivity clause is not present in contract"
    if indicators == 0:
        return FactorResult(
            factor = "exclusivity and duration",
            direction = FactorDirection.SELFEMPLOYMENT,
            strength = FactorStrength.MODERATE,
            evidence=f"{engagement_length}, {extension}, {exclusivity}",
            sufficiency="assessable",
        )
    if indicators == 1:
        return FactorResult(
            factor = "exclusivity and duration",
            direction = FactorDirection.SELFEMPLOYMENT,
            strength = FactorStrength.WEAK,
            evidence=f"{engagement_length}, {extension}, {exclusivity}",
            sufficiency="assessable",
        )
    if indicators == 2:
        return FactorResult(
            factor = "exclusivity and duration",
            direction = FactorDirection.EMPLOYMENT,
            strength = FactorStrength.MODERATE,
            evidence=f"{engagement_length}, {extension}, {exclusivity}",
            sufficiency="assessable",
        )
    if indicators >= 3:
        return FactorResult(
            factor = "exclusivity and duration",
            direction = FactorDirection.EMPLOYMENT,
            strength = FactorStrength.STRONG,
            evidence=f"{engagement_length}, {extension}, {exclusivity}",
            sufficiency="assessable",
        )
    


# Ai Integration for Gate1: Personal Service test
load_dotenv(override=True)
openrouter = OpenAI(
    api_key=os.getenv('OPENROUTER_API_KEY'),
    base_url="https://openrouter.ai/api/v1"
)

 
# model_gpt = "openai/gpt-5.6-luna"    #Decent speed 22 in 3min 10s
model_gpt = "google/gemini-3.5-flash-lite"     #Fastest by far 54.1s for all 22, but moderately expensive due to high amount of API calls used
# model_gpt = "deepseek/deepseek-v4.1-flash"   Deep Seek Was insanely slow over 1min 30 for 1 out of 22 



#Function used for user input in API callout, to provide assess gate 1 API call out with necessary information
def gate_1_facts(engagement):
    return f"""Contract states a right of substitution: {engagement.substitution_clause}
Right is fettered: {engagement.substitution_fettered}
Who would pay a substitute: {engagement.substitute_payment.value}

Account of substitution in practice:
{engagement.substitution_attempted}"""

#API call out for gate 1 personal service result, uses relevant law from law_content.py and detailed prompt from prompts.py
def assess_gate_1(engagement):
    system_prompt_gate1 = prompts.system_prompt_gate1
    messages_gate1 = [{"role": "system", "content": system_prompt_gate1},
      {"role": "user", "content": gate_1_facts(engagement)}]
    last_error = None
    for attempt in range(3):
        try:      
            response = openrouter.chat.completions.create(
                model = model_gpt,
                messages = messages_gate1,
                temperature = 0,
                )
            data_gate1 = json.loads(response.choices[0].message.content)
            return GateResult(
                outcome=GateOutcome(data_gate1['outcome']),
                reasoning=data_gate1['reasoning'],
                evidence=data_gate1['evidence'],
                contradiction=data_gate1['contradiction'],
            )
        except (json.JSONDecodeError, ValueError, KeyError) as err:
            last_error = err 
    return GateResult(
                    outcome=GateOutcome.UNCLEAR,
                    reasoning=f"Assessment failed: {last_error}",
                    evidence="",
                    contradiction="",
                )




#Function used for user input in API callout, to provide assess gate 2 API call out with necessary information
def gate_2_facts(engagement):
    return f"""Who decides what work and what order: {engagement.decides_what_work_and_what_order}
Who decides how work is performed: {engagement.decides_how_work_performed}
Who sets the hours and location: {engagement.hours_and_location_set}
Report to a manager or not:{engagement.report_to_a_manager}
"""
#API call out for gate 2 control test result, uses relevant law from law_content.py and detailed prompt from prompts.py
def assess_gate_2(engagement):
    system_prompt_gate2 = prompts.system_prompt_gate2
    messages_gate2 = [{"role": "system", "content": system_prompt_gate2},
      {"role": "user", "content": gate_2_facts(engagement)}]
    last_error = None
    for attempt in range(3):
        try:
            response = openrouter.chat.completions.create(
                model = model_gpt,
                messages = messages_gate2,
                temperature = 0,
                )
            data_gate2 = json.loads(response.choices[0].message.content)
            return GateResult(
                outcome=GateOutcome(data_gate2['outcome']),
                reasoning=data_gate2['reasoning'],
                evidence=data_gate2['evidence'],
            )
        except (json.JSONDecodeError, ValueError, KeyError) as err:
            last_error = err
    return GateResult(
            outcome=GateOutcome.UNCLEAR,
            reasoning=f"Assessment failed: {last_error}",
            evidence="",
        )



#AI integration for financial risk one of the two factors requiring LLM call out
#Function used for user input in API callout, to provide financial risk factor API call out with necessary information
def factor_financial_facts(engagement):
    return f"""
    Does defective work need correcting: {engagement.defective_work_corrected}
    Can they make a loss on engagement: {engagement.loss_on_engagement}
    """
#API call for assessing financial risk factor
def assess_factor_financial(engagement):
    system_prompt_financial_risk = prompts.system_prompt_financial_risk
    messages_factor_financial = [{"role": "system", "content": system_prompt_financial_risk},
      {"role": "user", "content": factor_financial_facts(engagement)}]
    last_error = None
    for attempt in range(3):
        try:
            response = openrouter.chat.completions.create(
                model = model_gpt,
                messages = messages_factor_financial,
                temperature = 0,
            )
            data = json.loads(response.choices[0].message.content)
            return FactorResult(
                factor = "financial risk",
                direction=FactorDirection(data['direction']),
                strength=FactorStrength(data['strength']),
                evidence=data['evidence'],
                sufficiency=data['sufficiency'],

            )
        except (json.JSONDecodeError, ValueError, KeyError) as err:
            last_error = err
    return FactorResult(
        factor="financial risk",
        direction=FactorDirection.NEUTRAL,
        strength=FactorStrength.WEAK,
        evidence=f"Assessment failed: {last_error}",
        sufficiency="insufficient",
    )

#AI Integration for organisation test
def factor_organisation_facts(engagement):
    return f"""
    Are they presented as part of the organisation: {engagement.presented_as_part_of_organisation}
    Do they have staff benefits or training: {engagement.staff_benefits_training_management}
    """

#API call for organisation factor 
def assess_factor_organisation(engagement):
    system_prompt_organisation = prompts.system_prompt_organisation
    messages_factor_organisation = [
        {"role": "system", "content": system_prompt_organisation},
        {"role": "user", "content": factor_organisation_facts(engagement)}
    ]
    last_error = None
    for attempt in range(3):
        try:
            response = openrouter.chat.completions.create(
                model=model_gpt,
                messages=messages_factor_organisation,
                temperature=0
            )
            data = json.loads(response.choices[0].message.content)
            return FactorResult(
                factor="integration",
                direction=FactorDirection(data['direction']),
                strength=FactorStrength(data['strength']),
                evidence=data['evidence'],
                sufficiency=data['sufficiency'],
            )
        except (json.JSONDecodeError, ValueError, KeyError) as err:
            last_error = err
    return FactorResult(
        factor="integration",
        direction=FactorDirection.NEUTRAL,
        strength=FactorStrength.WEAK,
        evidence=f"Assessment failed: {last_error}",
        sufficiency="insufficient",
    )


#Now creating band enum to provide overall analysis of all factors and gates providing an outcome of likely employment status
class Band(str, Enum):
    STRONG_EMPLOYMENT = "strong employment"
    LIKELY_EMPLOYMENT = "likely employment"
    BORDERLINE = "borderline"
    LIKELY_NOT_EMPLOYMENT = "likely not employment"
    STRONG_NOT_EMPLOYMENT = "strong not employment"


#Determine band LLM call (final result)
def band_facts(results):
    text = ""
    for r in results:
        text += f"Factor: {r.factor}. Direction: {r.direction.value}. Strength: {r.strength.value}. Sufficiency: {r.sufficiency}"
        text += "\n"
    return text

#Uses results from run function to provide an overall result
def determine_band(results):
    system_prompt_band = prompts.system_prompt_band
    messages = [{"role": "system", "content": system_prompt_band},
      {"role": "user", "content": band_facts(results)}]
    last_error = None
    for attempt in range(3):
        try:
            response = openrouter.chat.completions.create(
                model = model_gpt,
                messages = messages,
                temperature = 0,
            )
            json_band_choice = json.loads(response.choices[0].message.content)
            return Band(json_band_choice['band']), json_band_choice['reasoning']
        except (json.JSONDecodeError, ValueError, KeyError) as err:
            last_error = err
    return Band.BORDERLINE, f"Band could not be determined after 3 attempts: {last_error}"


#Dataclass used for formatting assessment results
@dataclass
class Assessment:
    gate1: GateResult
    reasoning: str
    gate2: Optional[GateResult] = None
    band: Optional[Band] = None
    results: list = field(default_factory=list)


# Sequential gateway: gate 1, then gate 2, then the six factors. A failed gate stops the analysis, since there can be no contract of service. Run provides results for determine band function
def run(engagement):
    results = []
    g1 = assess_gate_1(engagement)
    if g1.outcome == GateOutcome.FAIL:
        return Assessment(gate1=g1, reasoning="Gate 1 failed: no contract of service")
    g2 = assess_gate_2(engagement)
    if g2.outcome == GateOutcome.FAIL:
        return Assessment(gate1=g1, gate2=g2, reasoning="Gate 2 failed: no contract of service")
    results.append(assess_equipment(engagement))
    results.append(payment(engagement))
    results.append(in_business_on_own_account(engagement))
    results.append(exclusivity_and_duration(engagement))
    results.append(assess_factor_financial(engagement))
    results.append(assess_factor_organisation(engagement))
    band, reasoning = determine_band(results)
    return Assessment(gate1=g1, gate2=g2, band=band, reasoning=reasoning, results=results)



def format_assessment(assessment):
    if assessment.band == None:
        if assessment.gate2 is None:
            #Dedent module used so return is formatted correctly for markdown display
            return dedent(f"""\
            ## Not employment

            #### Analysis stopped at Gate 1 (personal service).

            **Reasoning:** {assessment.gate1.reasoning}

            **Evidence:** {assessment.gate1.evidence}
            """)
        else:
            return dedent(f"""\
            ## Not employment
            #### Passed gate 1 (personal service)
            #### Gate 1 — personal service
            **Reasoning:** {assessment.gate1.reasoning}

            **Evidence:** {assessment.gate1.evidence}

            Analysis stopped at Gate 2 (Control).
            #### Gate 2 — control
            **Reasoning:** {assessment.gate2.reasoning}

            **Evidence:** {assessment.gate2.evidence}
            """)
    #Both Gates Passed:
    text = dedent(f"""\
        ## {assessment.band.value}

        **Reasoning:** {assessment.reasoning}

        #### Gates
        Gate 1 (personal service): {assessment.gate1.outcome.value}

        Gate 2 (control): {assessment.gate2.outcome.value}

        #### Factors
        """)
    
    for r in assessment.results:
        text += dedent(f"""\
        **{r.factor}** - {r.direction.value} - {r.strength.value}

        {r.evidence}
        
        """)
    if assessment.gate1.contradiction:
        text += dedent(f"""\
            #### Contradiction

            {assessment.gate1.contradiction}
            """)

    return text





