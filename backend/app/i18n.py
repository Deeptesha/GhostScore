"""
Local-mode localisation of the backend's stub outputs (Hindi / Marathi).

⚙ LOCAL ONLY. In MODE=gcp, Gemini P7 (the localizer prompt) is the intended
translator; this table exists so the offline demo can show the language switch
working without calling a model. It only covers the fixed strings the local
stubs can produce. Unknown strings are returned unchanged.

NOTE: these translations were written by an AI assistant and have NOT been
reviewed by a native speaker. Have a Hindi speaker and a Marathi speaker check
them before any public demo.
"""
from __future__ import annotations
import re
from typing import Any

# English band name from the API -> label shown in the UI (UI scale is
# Building / Fair / Good / Excellent for Poor / Fair / Good / Excellent).
BAND_LABEL = {
    "hi": {"Poor": "शुरुआती", "Fair": "ठीक-ठाक", "Good": "अच्छा", "Excellent": "उत्कृष्ट"},
    "mr": {"Poor": "सुरुवातीचा", "Fair": "बरा", "Good": "चांगला", "Excellent": "उत्कृष्ट"},
}

# Exact-match strings: english -> {hi, mr}
_EXACT: dict[str, dict[str, str]] = {
    # factor labels (gemini._PLAIN_LABELS)
    "Regular bill payments": {"hi": "नियमित बिल भुगतान", "mr": "नियमित बिल भरणा"},
    "Steady monthly income": {"hi": "स्थिर मासिक आय", "mr": "स्थिर मासिक उत्पन्न"},
    "Responsible spending": {"hi": "ज़िम्मेदार खर्च", "mr": "जबाबदार खर्च"},
    "Digital payment activity": {"hi": "डिजिटल भुगतान गतिविधि", "mr": "डिजिटल पेमेंट हालचाल"},
    "Consistent rent payments": {"hi": "किराये का नियमित भुगतान", "mr": "भाड्याचा नियमित भरणा"},
    "Recent on-time streak": {"hi": "हाल के समय पर भुगतान", "mr": "अलीकडील वेळेवर भरणा"},
    "Share of bills paid in full": {"hi": "पूरे चुकाए गए बिलों का हिस्सा", "mr": "पूर्ण भरलेल्या बिलांचा हिस्सा"},
    "Bill amount swings": {"hi": "बिल की रकम में उतार-चढ़ाव", "mr": "बिलाच्या रकमेतील चढ-उतार"},
    "Regular money coming in": {"hi": "नियमित आमदनी", "mr": "नियमित येणारे पैसे"},
    "Longest payment delay": {"hi": "सबसे लंबी भुगतान देरी", "mr": "सर्वात मोठा भरणा विलंब"},
    "Credit line usage": {"hi": "क्रेडिट लाइन का उपयोग", "mr": "क्रेडिट लाइनचा वापर"},
    "Months of history provided": {"hi": "दिए गए इतिहास के महीने", "mr": "दिलेल्या इतिहासाचे महिने"},
    # plan titles
    "Add 2 more months of UPI history": {"hi": "UPI का 2 महीने का और इतिहास जोड़ें", "mr": "UPI चा आणखी 2 महिन्यांचा इतिहास जोडा"},
    "Upload missing rent receipts": {"hi": "छूटी हुई किराया रसीदें अपलोड करें", "mr": "राहिलेल्या भाडे पावत्या अपलोड करा"},
    "Show more consistent monthly income": {"hi": "मासिक आय ज़्यादा स्थिर दिखाएँ", "mr": "मासिक उत्पन्न अधिक स्थिर दाखवा"},
    "Upload 6 months of utility bills": {"hi": "6 महीने के उपयोगिता बिल अपलोड करें", "mr": "6 महिन्यांची युटिलिटी बिले अपलोड करा"},
    # plan reasons
    "More UPI transactions confirm your digital payment habit.": {"hi": "ज़्यादा UPI लेन-देन आपकी डिजिटल भुगतान की आदत की पुष्टि करते हैं।", "mr": "अधिक UPI व्यवहार तुमच्या डिजिटल पेमेंटच्या सवयीची खात्री देतात."},
    "Rental receipts prove consistent housing-expense reliability.": {"hi": "किराया रसीदें आवास खर्च के नियमित भुगतान का प्रमाण देती हैं।", "mr": "भाडे पावत्या घरखर्च नियमित भरल्याचा पुरावा देतात."},
    "Lower income swings signal a more predictable repayment capacity.": {"hi": "आय में कम उतार-चढ़ाव चुकाने की अधिक अनुमानित क्षमता दिखाता है।", "mr": "उत्पन्नातील कमी चढ-उतार परतफेडीची अधिक अंदाजे क्षमता दर्शवतात."},
    "Six months of utility bills gives the model stronger payment data.": {"hi": "छह महीने के बिल मॉडल को भुगतान का मज़बूत डेटा देते हैं।", "mr": "सहा महिन्यांची बिले मॉडेलला भरण्याचा अधिक भक्कम डेटा देतात."},
    "This action improves a key feature in your score.": {"hi": "यह कदम आपके स्कोर के एक अहम पहलू को बेहतर करता है।", "mr": "ही कृती तुमच्या स्कोअरमधील एक महत्त्वाचा घटक सुधारते."},
    # plan steps
    "Open your UPI app": {"hi": "अपना UPI ऐप खोलें", "mr": "तुमचे UPI ॲप उघडा"},
    "Export or screenshot the last 2 months": {"hi": "पिछले 2 महीनों का एक्सपोर्ट या स्क्रीनशॉट लें", "mr": "मागील 2 महिन्यांचा एक्सपोर्ट किंवा स्क्रीनशॉट घ्या"},
    "Upload on the Documents screen": {"hi": "दस्तावेज़ स्क्रीन पर अपलोड करें", "mr": "दस्तऐवज स्क्रीनवर अपलोड करा"},
    "Collect receipts from your landlord": {"hi": "मकान मालिक से रसीदें लें", "mr": "घरमालकाकडून पावत्या घ्या"},
    "Photograph clearly": {"hi": "साफ़ फ़ोटो लें", "mr": "स्पष्ट फोटो काढा"},
    "Consider stable side income sources": {"hi": "अतिरिक्त स्थिर आमदनी के साधन देखें", "mr": "अतिरिक्त स्थिर उत्पन्नाचे स्रोत विचारात घ्या"},
    "Keep monthly inflow more consistent over 3 months": {"hi": "3 महीनों तक हर महीने की आमदनी ज़्यादा एक जैसी रखें", "mr": "3 महिने मासिक उत्पन्न अधिक सारखे ठेवा"},
    "Collect electricity/water bills for the last 6 months": {"hi": "पिछले 6 महीनों के बिजली/पानी के बिल इकट्ठा करें", "mr": "मागील 6 महिन्यांची वीज/पाणी बिले गोळा करा"},
    "Follow up with your GhostScore advisor.": {"hi": "अपने GhostScore सलाहकार से बात करें।", "mr": "तुमच्या GhostScore सल्लागाराशी बोला."},
    # loan options (stub P4)
    "You may be eligible for a Mudra Shishu loan [P1].": {"hi": "आप मुद्रा शिशु ऋण के लिए पात्र हो सकते हैं [P1]।", "mr": "तुम्ही मुद्रा शिशु कर्जासाठी पात्र असू शकता [P1]."},
    "Up to INR 50,000 without collateral [P1].": {"hi": "बिना गिरवी के INR 50,000 तक [P1]।", "mr": "तारणाशिवाय INR 50,000 पर्यंत [P1]."},
    "With a Good or better band you may be eligible for Mudra Kishore [P2].": {"hi": "अच्छी या बेहतर श्रेणी में आप मुद्रा किशोर के लिए पात्र हो सकते हैं [P2]।", "mr": "चांगली किंवा त्याहून चांगली श्रेणी असल्यास तुम्ही मुद्रा किशोरसाठी पात्र असू शकता [P2]."},
    "INR 50,001 to INR 5,00,000 with income-generating activity evidence [P2].": {"hi": "आय देने वाली गतिविधि के प्रमाण के साथ INR 50,001 से INR 5,00,000 [P2]।", "mr": "उत्पन्न देणाऱ्या कामाच्या पुराव्यासह INR 50,001 ते INR 5,00,000 [P2]."},
    "No matching product found in the retrieved passages.": {"hi": "प्राप्त अंशों में कोई मेल खाता उत्पाद नहीं मिला।", "mr": "मिळालेल्या उताऱ्यांमध्ये जुळणारे उत्पादन आढळले नाही."},
    # document review (stub P1)
    "No action needed.": {"hi": "कोई कार्रवाई ज़रूरी नहीं।", "mr": "कोणतीही कृती आवश्यक नाही."},
    "Please re-upload the document with clearer details.": {"hi": "कृपया ज़्यादा साफ़ जानकारी के साथ दस्तावेज़ दोबारा अपलोड करें।", "mr": "कृपया अधिक स्पष्ट तपशीलांसह दस्तऐवज पुन्हा अपलोड करा."},
    # disclaimer returned by the API
    "Model estimate — not a lender decision.": {"hi": "मॉडल का अनुमान — यह किसी ऋणदाता का निर्णय नहीं है।", "mr": "मॉडेलचा अंदाज — हा कर्जदात्याचा निर्णय नाही."},
}

# Templated strings: (regex, {lang: template}). Templates use {1}, {2}, ... for groups.
_PATTERNS: list[tuple[re.Pattern, dict[str, str]]] = [
    (re.compile(r"^Your payments earned you a (\w+) credit band\.$"),
     {"hi": "आपके भुगतानों के आधार पर आपकी क्रेडिट श्रेणी: {1}।",
      "mr": "तुमच्या भरण्यांच्या आधारे तुमची क्रेडिट श्रेणी: {1}."}),
    (re.compile(r"^This is a model estimate with (\d+)% confidence, not a lender decision\. More months of data would increase accuracy\.$"),
     {"hi": "यह मॉडल का अनुमान है, जिसमें {1}% भरोसा है। यह किसी ऋणदाता का निर्णय नहीं है। ज़्यादा महीनों का डेटा देने से सटीकता बढ़ेगी।",
      "mr": "हा मॉडेलचा अंदाज आहे, ज्यामध्ये {1}% खात्री आहे. हा कर्जदात्याचा निर्णय नाही. अधिक महिन्यांचा डेटा दिल्यास अचूकता वाढेल."}),
    (re.compile(r"^([+-]\d+) points$"),
     {"hi": "{1} अंक", "mr": "{1} गुण"}),
    (re.compile(r"^⚙ \[STUB\] Your current band is (\w+) \(score (\d+)\)\. To improve, consider uploading more months of utility bills or UPI history\. Would you like to see what-if estimates for specific actions\?$"),
     {"hi": "⚙ [डेमो उत्तर] आपकी मौजूदा श्रेणी: {1} (स्कोर {2})। सुधार के लिए बिजली-पानी के बिल या UPI इतिहास के और महीने अपलोड करें। क्या आप किसी खास कदम का अनुमान देखना चाहेंगे?",
      "mr": "⚙ [डेमो उत्तर] तुमची सध्याची श्रेणी: {1} (स्कोअर {2}). सुधारण्यासाठी वीज-पाणी बिले किंवा UPI इतिहासाचे आणखी महिने अपलोड करा. विशिष्ट कृतींचे अंदाज पाहायचे आहेत का?"}),
]


def tr(text: str, lang: str) -> str:
    """Translate one known stub string. Unknown strings are returned unchanged."""
    if lang not in ("hi", "mr") or not isinstance(text, str):
        return text
    hit = _EXACT.get(text)
    if hit:
        return hit[lang]
    for rx, templates in _PATTERNS:
        m = rx.match(text)
        if m:
            groups = list(m.groups())
            # band names inside templates use the localised UI label
            groups = [BAND_LABEL[lang].get(g, g) for g in groups]
            out = templates[lang]
            for i, g in enumerate(groups, start=1):
                out = out.replace("{%d}" % i, g)
            return out
    return text


def localize(obj: Any, lang: str) -> Any:
    """Recursively translate every known string value in a dict/list structure."""
    if lang not in ("hi", "mr"):
        return obj
    if isinstance(obj, str):
        return tr(obj, lang)
    if isinstance(obj, list):
        return [localize(x, lang) for x in obj]
    if isinstance(obj, dict):
        return {k: localize(v, lang) for k, v in obj.items()}
    return obj
