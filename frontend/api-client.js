/**
 * GhostScore frontend client.
 *
 * The Stitch export is a static mock with hard-coded sample content (and some
 * invented claims such as score weights and fairness metrics). This script keeps
 * the Stitch header, bottom nav and design tokens, and renders each screen's
 * <main> content from the live API (Section 16 contract).
 *
 * Screen flow (Section 15): welcome -> upload -> review -> score -> plan | chat | options
 */
(function (window) {
  "use strict";

  const API = window.GHOSTSCORE_API_URL || window.location.origin;
  const SCREENS = {
    welcome: "ghostscore_welcome_consent",
    upload:  "ghostscore_upload_documents",
    review:  "ghostscore_document_check_results",
    score:   "ghostscore_score_dashboard",
    plan:    "ghostscore_improvement_plan",
    chat:    "ghostscore_advisor_chat",
    options: "ghostscore_eligible_loan_products",
    history: "ghostscore_score_trend_history",
    audit:   "ghostscore_audit_view_for_judges",
    dash:    "ghostscore_desktop_dashboard_overview",
    dloans:  "ghostscore_desktop_loan_options",
  };
  const DOC_TYPES = [
    { type: "electricity_bill", label: "Electricity Bill",        icon: "bolt",    hint: "Utility bill showing amount, due date and paid date" },
    { type: "rent_receipt",     label: "Rent Receipt",            icon: "home",    hint: "Monthly rent receipt or landlord confirmation" },
    { type: "upi_screenshot",   label: "Mobile Recharge / UPI",   icon: "qr_code", hint: "Screenshot of a UPI payment" },
  ];
  // The UI scale is 300-579 / 580-669 / 670-739 / 740-850 (backend uses the same cut-offs).
  const BANDS = [
    { api: "Poor",      label: "Building",  range: "300-579" },
    { api: "Fair",      label: "Fair",      range: "580-669" },
    { api: "Good",      label: "Good",      range: "670-739" },
    { api: "Excellent", label: "Excellent", range: "740-850" },
  ];

  // ── state (survives page navigation within the tab) ──────────────────────
  const store = {
    get(k, d) { try { return JSON.parse(sessionStorage.getItem("gs_" + k)) ?? d; } catch (e) { return d; } },
    set(k, v) { sessionStorage.setItem("gs_" + k, JSON.stringify(v)); },
  };
  const cfg = { userId: "priya", language: store.get("lang", "en") };


  // ── i18n ─────────────────────────────────────────────────────────────────
  // Keyed on the English string; value is [Hindi, Marathi]. These translations
  // were drafted by an AI assistant and have NOT been reviewed by a native speaker.
  // Generated text (score headline, plan, loan options, chat) is localised by the
  // backend (local mode: fixed table in app/i18n.py; gcp mode: Gemini P7).
  const D = {
    // welcome (static Stitch text)
    "Dignity-first Credit Engine": ["सम्मान-प्रथम क्रेडिट इंजन", "सन्मान-प्रथम क्रेडिट इंजिन"],
    "Your payments tell your story.": ["आपके भुगतान आपकी कहानी कहते हैं।", "तुमचे पेमेंट तुमची गोष्ट सांगतात."],
    "You don't need a formal bank credit history to prove your creditworthiness. Everyday cash flow, bills, and payments prove your diligence.": ["अपनी साख साबित करने के लिए औपचारिक बैंक क्रेडिट इतिहास ज़रूरी नहीं है। रोज़ की आमदनी, बिल और भुगतान आपकी मेहनत और ज़िम्मेदारी दिखाते हैं।", "तुमची पत सिद्ध करण्यासाठी बँकेचा औपचारिक क्रेडिट इतिहास लागत नाही. रोजचे उत्पन्न, बिले आणि पेमेंट तुमची मेहनत आणि जबाबदारी दाखवतात."],
    "How GhostScore Works": ["GhostScore कैसे काम करता है", "GhostScore कसे काम करते"],
    "1. Share bills & UPI receipts": ["1. बिल और UPI रसीदें साझा करें", "1. बिले आणि UPI पावत्या शेअर करा"],
    "Add electricity, rent, or mobile recharge records you already pay every month.": ["बिजली, किराया या मोबाइल रिचार्ज के वे रिकॉर्ड जोड़ें जो आप हर महीने भरते हैं।", "वीज, भाडे किंवा मोबाइल रिचार्जचे जे रेकॉर्ड तुम्ही दर महिन्याला भरता ते जोडा."],
    "2. Get your GhostScore": ["2. अपना GhostScore पाएँ", "2. तुमचा GhostScore मिळवा"],
    "Our machine learning builds your score based on reliability, not existing bank loans.": ["हमारा मशीन लर्निंग मॉडल आपका स्कोर भुगतान की नियमितता के आधार पर बनाता है, मौजूदा बैंक लोन के आधार पर नहीं।", "आमचे मशीन लर्निंग मॉडेल तुमचा स्कोर पेमेंटच्या नियमिततेवर बनवते, सध्याच्या बँक कर्जांवर नाही."],
    "3. Unlock fair loans & improve": ["3. उचित लोन पाएँ और सुधार करें", "3. योग्य कर्जे मिळवा आणि सुधारणा करा"],
    "See plain-language steps to boost your rating and qualify for low-interest micro-loans.": ["अपनी रेटिंग बढ़ाने और कम ब्याज के छोटे लोन के लिए पात्र होने के आसान कदम देखें।", "तुमची रेटिंग वाढवण्याचे आणि कमी व्याजाच्या छोट्या कर्जांसाठी पात्र होण्याचे सोपे टप्पे पहा."],
    "Your Data Rights & Control": ["आपके डेटा के अधिकार और नियंत्रण", "तुमचे डेटा हक्क आणि नियंत्रण"],
    "You remain in full ownership": ["पूरा मालिकाना हक़ आपके पास रहता है", "पूर्ण मालकी तुमच्याकडेच राहते"],
    "Our Promise:": ["हमारा वादा:", "आमचे वचन:"],
    "We only read transaction amounts and dates to assess payment consistency. We never sell your data or share it without your permission.": ["हम भुगतान की नियमितता जाँचने के लिए सिर्फ़ लेन-देन की रकम और तारीखें पढ़ते हैं। आपकी अनुमति के बिना हम आपका डेटा न बेचते हैं, न साझा करते हैं।", "पेमेंटची नियमितता तपासण्यासाठी आम्ही फक्त व्यवहारांची रक्कम आणि तारखा वाचतो. तुमच्या परवानगीशिवाय आम्ही तुमचा डेटा विकत नाही किंवा शेअर करत नाही."],
    "Select data you choose to link": ["जो डेटा जोड़ना चाहें, उसे चुनें", "जोडायचा डेटा निवडा"],
    "Utility & Electricity Bills": ["यूटिलिटी और बिजली के बिल", "युटिलिटी आणि वीज बिले"],
    "Check payment timeliness & consistency": ["भुगतान समय पर और नियमित है या नहीं, जाँचें", "पेमेंट वेळेवर आणि नियमित आहे का ते तपासा"],
    "Rent Receipts & Landlord Confirmation": ["किराया रसीदें और मकान-मालिक की पुष्टि", "भाडे पावत्या आणि घरमालकाची पुष्टी"],
    "Demonstrate fixed recurring payment reliability": ["नियमित तय भुगतान की भरोसेमंदी दिखाएँ", "ठरलेल्या नियमित पेमेंटची विश्वासार्हता दाखवा"],
    "UPI QR & Merchant History": ["UPI QR और व्यापारी इतिहास", "UPI QR आणि व्यापारी इतिहास"],
    "Show daily digital business cash flows": ["रोज़ का डिजिटल कारोबारी लेन-देन दिखाएँ", "रोजचे डिजिटल व्यवसाय व्यवहार दाखवा"],
    "Delete my data anytime": ["मेरा डेटा कभी भी हटाएँ", "माझा डेटा केव्हाही हटवा"],
    "Continue to Build GhostScore": ["GhostScore बनाना जारी रखें", "GhostScore बनवणे सुरू ठेवा"],
    "This is an estimate, not a loan decision. Checking does not hurt your credit standing or alert credit bureaus.": ["यह एक अनुमान है, लोन का फ़ैसला नहीं। इसे देखने से आपकी क्रेडिट स्थिति पर असर नहीं पड़ता और क्रेडिट ब्यूरो को कोई सूचना नहीं जाती।", "हा अंदाज आहे, कर्जाचा निर्णय नाही. हे पाहिल्याने तुमच्या क्रेडिट स्थितीवर परिणाम होत नाही आणि क्रेडिट ब्युरोला कळवले जात नाही."],
    // nav + header subtitle
    "Home": ["होम", "मुख्यपृष्ठ"], "Documents": ["दस्तावेज़", "कागदपत्रे"], "Score": ["स्कोर", "स्कोर"], "Advisor": ["सलाहकार", "सल्लागार"],
    // chat (static Stitch text)
    "Online • Credit Coach": ["ऑनलाइन • क्रेडिट कोच", "ऑनलाइन • क्रेडिट कोच"],
    "Your Score": ["आपका स्कोर", "तुमचा स्कोर"],
    "Tap to ask quickly:": ["जल्दी पूछने के लिए टैप करें:", "पटकन विचारण्यासाठी टॅप करा:"],
    "What lowers my score?": ["मेरा स्कोर क्या घटाता है?", "माझा स्कोर कशामुळे कमी होतो?"],
    "What loan fits me?": ["मेरे लिए कौन सा लोन ठीक रहेगा?", "माझ्यासाठी कोणते कर्ज योग्य आहे?"],
    "What if I upload more bills?": ["अगर मैं और बिल अपलोड करूँ तो?", "मी आणखी बिले अपलोड केली तर?"],
    "Can I fix the rent receipt?": ["क्या किराया रसीद ठीक की जा सकती है?", "भाडे पावती दुरुस्त करता येईल का?"],
    "Listening to your voice...": ["आपकी आवाज़ सुन रहे हैं...", "तुमचा आवाज ऐकत आहे..."],
    "Speak in Hindi, Marathi, or English": ["हिंदी, मराठी या अंग्रेज़ी में बोलें", "हिंदी, मराठी किंवा इंग्रजीत बोला"],
    "Send message": ["संदेश भेजें", "संदेश पाठवा"],
    "Speak your question": ["अपना सवाल बोलें", "तुमचा प्रश्न बोला"],
    "Hello, I am your GhostScore advisor. I can explain your band, what-if estimates and loan options. I do not make credit decisions.": ["नमस्ते, मैं आपका GhostScore सलाहकार हूँ। मैं आपकी श्रेणी, \"अगर ऐसा करें तो\" के अनुमान और लोन विकल्प समझा सकता हूँ। मैं क्रेडिट का फ़ैसला नहीं करता।", "नमस्कार, मी तुमचा GhostScore सल्लागार आहे. मी तुमची श्रेणी, \"असे केले तर\" चे अंदाज आणि कर्ज पर्याय समजावून सांगू शकतो. मी क्रेडिटचा निर्णय घेत नाही."],
    "Sorry, something went wrong:": ["क्षमा करें, कुछ गड़बड़ हुई:", "क्षमस्व, काहीतरी चुकले:"],
    // upload
    "Electricity Bill": ["बिजली का बिल", "वीज बिल"],
    "Utility bill showing amount, due date and paid date": ["रकम, देय तारीख और भुगतान की तारीख वाला बिल", "रक्कम, देय तारीख आणि भरल्याची तारीख असलेले बिल"],
    "Rent Receipt": ["किराया रसीद", "भाडे पावती"],
    "Monthly rent receipt or landlord confirmation": ["मासिक किराया रसीद या मकान-मालिक की पुष्टि", "मासिक भाडे पावती किंवा घरमालकाची पुष्टी"],
    "Mobile Recharge / UPI": ["मोबाइल रिचार्ज / UPI", "मोबाइल रिचार्ज / UPI"],
    "Screenshot of a UPI payment": ["UPI भुगतान का स्क्रीनशॉट", "UPI पेमेंटचा स्क्रीनशॉट"],
    "Added ({n})": ["जोड़ा गया ({n})", "जोडले ({n})"],
    "Not added": ["जोड़ा नहीं गया", "जोडलेले नाही"],
    "Uploading…": ["अपलोड हो रहा है…", "अपलोड होत आहे…"],
    "Error": ["त्रुटि", "त्रुटी"],
    "Choose file": ["फ़ाइल चुनें", "फाइल निवडा"],
    "Use sample": ["नमूना इस्तेमाल करें", "नमुना वापरा"],
    "Upload Payment Records": ["भुगतान रिकॉर्ड अपलोड करें", "पेमेंट रेकॉर्ड अपलोड करा"],
    "Every regular payment adds to your picture. Add what you have.": ["हर नियमित भुगतान आपकी तस्वीर को मज़बूत करता है। जो आपके पास है वह जोड़ें।", "प्रत्येक नियमित पेमेंट तुमचे चित्र मजबूत करते. तुमच्याकडे जे आहे ते जोडा."],
    "Demo build:": ["डेमो संस्करण:", "डेमो आवृत्ती:"],
    "Document extraction is a labelled stub in local mode. It returns sample fields for the document type and does not read your file. \"Use sample\" uploads a placeholder file.": ["लोकल मोड में दस्तावेज़ पढ़ना एक चिह्नित नकली (स्टब) हिस्सा है। यह दस्तावेज़ के प्रकार के हिसाब से नमूना फ़ील्ड लौटाता है और आपकी फ़ाइल नहीं पढ़ता। \"नमूना इस्तेमाल करें\" एक खाली प्लेसहोल्डर फ़ाइल अपलोड करता है।", "लोकल मोडमध्ये कागदपत्र वाचणे हा चिन्हांकित नकली (स्टब) भाग आहे. तो कागदपत्राच्या प्रकारानुसार नमुना फील्ड देतो आणि तुमची फाइल वाचत नाही. \"नमुना वापरा\" प्लेसहोल्डर फाइल अपलोड करतो."],
    "{n} document(s) added": ["{n} दस्तावेज़ जोड़े गए", "{n} कागदपत्रे जोडली"],
    "Review added documents": ["जोड़े गए दस्तावेज़ देखें", "जोडलेली कागदपत्रे तपासा"],
    "Add at least one document first.": ["पहले कम से कम एक दस्तावेज़ जोड़ें।", "आधी किमान एक कागदपत्र जोडा."],
    // review
    "No documents added yet.": ["अभी तक कोई दस्तावेज़ नहीं जोड़ा गया।", "अजून कोणतेही कागदपत्र जोडलेले नाही."],
    "Add documents": ["दस्तावेज़ जोड़ें", "कागदपत्रे जोडा"],
    "Check your documents": ["अपने दस्तावेज़ जाँचें", "तुमची कागदपत्रे तपासा"],
    "Here is what we read from each one.": ["हर दस्तावेज़ से हमने यह पढ़ा है।", "प्रत्येक कागदपत्रातून आम्ही हे वाचले."],
    "Calculate my score": ["मेरा स्कोर निकालें", "माझा स्कोर काढा"],
    "Add more documents": ["और दस्तावेज़ जोड़ें", "आणखी कागदपत्रे जोडा"],
    "Name": ["नाम", "नाव"], "Biller / landlord": ["बिल जारीकर्ता / मकान-मालिक", "बिल देणारा / घरमालक"], "Amount": ["रकम", "रक्कम"],
    "Due date": ["देय तारीख", "देय तारीख"], "Paid date": ["भुगतान की तारीख", "भरल्याची तारीख"], "Period": ["अवधि", "कालावधी"],
    "Accepted": ["स्वीकार किया गया", "स्वीकारले"], "Needs review": ["जाँच ज़रूरी", "तपासणी आवश्यक"], "Unreadable": ["पढ़ा नहीं जा सका", "वाचता आले नाही"],
    "Could not load review:": ["जाँच लोड नहीं हो सकी:", "तपासणी लोड होऊ शकली नाही:"],
    "Calculating…": ["निकाल रहे हैं…", "काढत आहे…"],
    "Score calculation failed:": ["स्कोर की गणना विफल रही:", "स्कोरची गणना अयशस्वी:"],
    // score
    "No score yet. Add your documents to get one.": ["अभी स्कोर नहीं है। स्कोर पाने के लिए दस्तावेज़ जोड़ें।", "अजून स्कोर नाही. स्कोर मिळवण्यासाठी कागदपत्रे जोडा."],
    "Namaste, {name}": ["नमस्ते, {name}", "नमस्कार, {name}"],
    "Synthetic demo persona": ["काल्पनिक डेमो व्यक्ति", "काल्पनिक डेमो व्यक्ती"],
    "Credit Readiness": ["क्रेडिट तैयारी", "क्रेडिट तयारी"],
    "Model estimate": ["मॉडल का अनुमान", "मॉडेलचा अंदाज"],
    "out of 850": ["850 में से", "850 पैकी"],
    "Updated {date}": ["अपडेट: {date}", "अपडेट: {date}"],
    "Signals the model leans on most": ["वे संकेत जिन पर मॉडल सबसे ज़्यादा निर्भर है", "ज्या संकेतांवर मॉडेल सर्वाधिक अवलंबून आहे"],
    "Signals the model leans on least": ["वे संकेत जिन पर मॉडल सबसे कम निर्भर है", "ज्या संकेतांवर मॉडेल सर्वात कमी अवलंबून आहे"],
    "Nothing stands out yet.": ["अभी कुछ खास नहीं दिख रहा।", "अजून काही विशेष दिसत नाही."],
    "model weight {n}%": ["मॉडल वज़न {n}%", "मॉडेल वजन {n}%"],
    "\"Model weight\" is how much a signal matters to the model for everyone. It is not a personal point value, and this build does not yet compute per-applicant attribution.": ["\u201cमॉडल वज़न\u201d बताता है कि कोई संकेत मॉडल के लिए सभी लोगों के लिए औसतन कितना मायने रखता है। यह आपका निजी अंक-मूल्य नहीं है, और यह संस्करण अभी हर आवेदक के लिए अलग योगदान नहीं निकालता।", "\u201cमॉडेल वजन\u201d म्हणजे एखादा संकेत सर्वांसाठी मॉडेलला किती महत्त्वाचा आहे. हे तुमचे वैयक्तिक गुणमूल्य नाही, आणि ही आवृत्ती अद्याप प्रत्येक अर्जदारासाठी स्वतंत्र योगदान काढत नाही."],
    "See my improvement plan": ["मेरी सुधार योजना देखें", "माझी सुधारणा योजना पहा"],
    "Loan options for me": ["मेरे लिए लोन विकल्प", "माझ्यासाठी कर्ज पर्याय"],
    "Ask the advisor": ["सलाहकार से पूछें", "सल्लागाराला विचारा"],
    "Score history": ["स्कोर इतिहास", "स्कोर इतिहास"],
    "Back to score": ["स्कोर पर वापस", "स्कोरकडे परत"],
    "Model estimate, not a lender decision.": ["मॉडल का अनुमान, कर्जदाता का फ़ैसला नहीं।", "मॉडेलचा अंदाज, कर्जदात्याचा निर्णय नाही."],
    "Demo build: trained on public Taiwan 2009 credit-card data and run on synthetic personas. No India-validated accuracy is claimed.": ["डेमो संस्करण: सार्वजनिक ताइवान 2009 क्रेडिट-कार्ड डेटा पर प्रशिक्षित और काल्पनिक व्यक्तियों पर चलाया गया। भारत में जाँची गई सटीकता का कोई दावा नहीं है।", "डेमो आवृत्ती: सार्वजनिक तैवान 2009 क्रेडिट-कार्ड डेटावर प्रशिक्षित आणि काल्पनिक व्यक्तींवर चालवलेली. भारतात पडताळलेल्या अचूकतेचा कोणताही दावा नाही."],
    // plan
    "Get a score first to see a plan.": ["योजना देखने के लिए पहले स्कोर पाएँ।", "योजना पाहण्यासाठी आधी स्कोर मिळवा."],
    "Your Score Improvement Plan": ["आपकी स्कोर सुधार योजना", "तुमची स्कोर सुधारणा योजना"],
    "Each estimate below comes from re-scoring your profile with that change. They are not added together.": ["नीचे हर अनुमान उस बदलाव के साथ आपकी प्रोफ़ाइल का स्कोर दोबारा निकालकर आया है। इन्हें जोड़ा नहीं जाता।", "खालील प्रत्येक अंदाज त्या बदलासह तुमच्या प्रोफाइलचा स्कोर पुन्हा काढून आलेला आहे. ते एकमेकांत मिळवले जात नाहीत."],
    "Today": ["आज", "आज"],
    "Best single step": ["सबसे असरदार एक कदम", "सर्वात प्रभावी एक पाऊल"],
    "Step {n}": ["कदम {n}", "पाऊल {n}"],
    "No improvement steps available right now.": ["अभी कोई सुधार कदम उपलब्ध नहीं है।", "सध्या कोणतेही सुधारणा टप्पे उपलब्ध नाहीत."],
    "Point changes are model re-score estimates, not guarantees.": ["अंकों में बदलाव मॉडल के दोबारा स्कोर के अनुमान हैं, गारंटी नहीं।", "गुणांतील बदल हे मॉडेलच्या पुनर्गणनेचे अंदाज आहेत, हमी नाहीत."],
    // options
    "Loan Options for You": ["आपके लिए लोन विकल्प", "तुमच्यासाठी कर्ज पर्याय"],
    "Based on your {band} band ({score}).": ["आपकी {band} श्रेणी ({score}) के आधार पर।", "तुमच्या {band} श्रेणीवर ({score}) आधारित."],
    "No score yet, so showing general options.": ["अभी स्कोर नहीं है, इसलिए सामान्य विकल्प दिखा रहे हैं।", "अजून स्कोर नाही, म्हणून सामान्य पर्याय दाखवत आहे."],
    "Checking here does not affect any credit profile.": ["यहाँ देखने से किसी क्रेडिट प्रोफ़ाइल पर असर नहीं पड़ता।", "येथे पाहिल्याने कोणत्याही क्रेडिट प्रोफाइलवर परिणाम होत नाही."],
    "May be eligible": ["पात्र हो सकते हैं", "पात्र असू शकता"],
    "Source passages:": ["स्रोत अंश:", "स्रोत उतारे:"],
    "Cannot confirm yet": ["अभी पुष्टि नहीं हो सकती", "अजून खात्री करता येत नाही"],
    "Only a regulated lender can decide on a loan. These are possibilities drawn from the policy passages shown (local mode uses a small labelled stub set, not live Vertex AI Search).": ["लोन पर फ़ैसला सिर्फ़ विनियमित कर्जदाता ही कर सकता है। ये दिखाए गए नीति-अंशों से निकली संभावनाएँ हैं (लोकल मोड में छोटा चिह्नित स्टब सेट इस्तेमाल होता है, लाइव Vertex AI Search नहीं)।", "कर्जाबाबत निर्णय फक्त नियमन केलेला कर्जदाताच घेऊ शकतो. हे दाखवलेल्या धोरण-उताऱ्यांतून आलेले संभाव्य पर्याय आहेत (लोकल मोडमध्ये छोटा चिन्हांकित स्टब संच वापरला जातो, थेट Vertex AI Search नाही)."],
    // history + audit
    "No score history yet.": ["अभी तक कोई स्कोर इतिहास नहीं है।", "अजून स्कोर इतिहास नाही."],
    "Score computed": ["स्कोर निकाला गया", "स्कोर काढला"],
    "Audit trail": ["ऑडिट ट्रेल", "ऑडिट ट्रेल"],
    "Every score is logged with model version, band and top factors.": ["हर स्कोर मॉडल संस्करण, श्रेणी और मुख्य कारकों के साथ दर्ज होता है।", "प्रत्येक स्कोर मॉडेल आवृत्ती, श्रेणी आणि प्रमुख घटकांसह नोंदवला जातो."],
    "Time": ["समय", "वेळ"], "Event": ["घटना", "घटना"], "Band": ["श्रेणी", "श्रेणी"], "Top factors": ["मुख्य कारक", "प्रमुख घटक"], "Model": ["मॉडल", "मॉडेल"], "Explanation id": ["स्पष्टीकरण आईडी", "स्पष्टीकरण आयडी"],
    "No scores logged yet.": ["अभी कोई स्कोर दर्ज नहीं है।", "अजून कोणताही स्कोर नोंदवलेला नाही."],
    "Fairness / demographic-parity metrics are not computed in this build, so none are shown.": ["इस संस्करण में निष्पक्षता / जनसांख्यिकीय समानता के मापदंड नहीं निकाले जाते, इसलिए कोई नहीं दिखाया गया।", "या आवृत्तीत निष्पक्षता / लोकसंख्याशास्त्रीय समानतेचे मापदंड काढले जात नाहीत, म्हणून काहीही दाखवलेले नाही."],
    "Demo build: data is held in server memory only and is cleared on restart. No delete-account flow is implemented yet.": ["डेमो संस्करण: डेटा सिर्फ़ सर्वर की मेमोरी में रहता है और रीस्टार्ट पर मिट जाता है। खाता हटाने की सुविधा अभी बनी नहीं है।", "डेमो आवृत्ती: डेटा फक्त सर्व्हरच्या मेमरीत राहतो आणि रीस्टार्टवर पुसला जातो. खाते हटवण्याची सुविधा अजून बनवलेली नाही."],
  };
  // Desktop (website) layout strings. Same caveat: AI-drafted, not native-reviewed.
  Object.assign(D, {
    "Alternative Credit & Advisor": ["वैकल्पिक क्रेडिट और सलाहकार", "पर्यायी क्रेडिट आणि सल्लागार"],
    "Overview / Home": ["अवलोकन / होम", "आढावा / मुख्यपृष्ठ"],
    "Document Vault": ["दस्तावेज़ वॉल्ट", "कागदपत्र वॉल्ट"],
    "Credit Score & Journey": ["क्रेडिट स्कोर और सफ़र", "क्रेडिट स्कोर आणि प्रवास"],
    "Loan Options": ["लोन विकल्प", "कर्ज पर्याय"],
    "Improvement Plan": ["सुधार योजना", "सुधारणा योजना"],
    "Advisor AI": ["AI सलाहकार", "AI सल्लागार"],
    "Audit & Compliance": ["ऑडिट और अनुपालन", "ऑडिट आणि अनुपालन"],
    "Demo profile: documents are placeholders in local mode.": ["डेमो प्रोफ़ाइल: लोकल मोड में दस्तावेज़ नमूना (प्लेसहोल्डर) हैं।", "डेमो प्रोफाइल: लोकल मोडमध्ये कागदपत्रे नमुना (प्लेसहोल्डर) आहेत."],
    "Documents Added": ["जोड़े गए दस्तावेज़", "जोडलेली कागदपत्रे"],
    "{n} of {m} types": ["{m} में से {n} प्रकार", "{m} पैकी {n} प्रकार"],
    "Demo sample files": ["डेमो नमूना फ़ाइलें", "डेमो नमुना फाइल्स"],
    "Model Confidence": ["मॉडल का भरोसा", "मॉडेलचा विश्वास"],
    "{n} possible": ["{n} संभावित", "{n} संभाव्य"],
    "See details →": ["विवरण देखें →", "तपशील पहा →"],
    "GhostScore Alternative Index": ["GhostScore वैकल्पिक सूचकांक", "GhostScore पर्यायी निर्देशांक"],
    "Estimated from the payment documents you added": ["आपके जोड़े गए भुगतान दस्तावेज़ों से अनुमानित", "तुम्ही जोडलेल्या पेमेंट कागदपत्रांवरून अंदाजित"],
    "Model confidence {n}%": ["मॉडल का भरोसा {n}%", "मॉडेलचा विश्वास {n}%"],
    "{band} (You)": ["{band} (आप)", "{band} (तुम्ही)"],
    "View tier progression steps": ["श्रेणी बढ़ाने के कदम देखें", "श्रेणी वाढवण्याचे टप्पे पहा"],
    "Possibilities, not approvals": ["संभावनाएँ, मंज़ूरी नहीं", "शक्यता, मंजुरी नाही"],
    "{n} possible loan options": ["{n} संभावित लोन विकल्प", "{n} संभाव्य कर्ज पर्याय"],
    "These come from the policy passages shown, not from an approval. Only a regulated lender can decide.": ["ये दिखाए गए नीति-अंशों से आए हैं, मंज़ूरी नहीं हैं। फ़ैसला सिर्फ़ विनियमित कर्जदाता कर सकता है।", "हे दाखवलेल्या धोरण-उताऱ्यांतून आलेले आहेत, मंजुरी नाही. निर्णय फक्त नियमन केलेला कर्जदाताच घेऊ शकतो."],
    "Explore loan options": ["लोन विकल्प देखें", "कर्ज पर्याय पहा"],
    "Why this score?": ["यह स्कोर कैसे बनता है?", "हा स्कोर कसा बनतो?"],
    "Traditional bureau scores depend on prior formal loans and credit cards. If you have never borrowed from a bank, you may have no score at all.": ["पारंपरिक ब्यूरो स्कोर पहले के औपचारिक लोन और क्रेडिट कार्ड पर निर्भर करते हैं। अगर आपने बैंक से कभी उधार नहीं लिया, तो हो सकता है आपका कोई स्कोर ही न हो।", "पारंपरिक ब्युरो स्कोर आधीच्या औपचारिक कर्जे आणि क्रेडिट कार्डवर अवलंबून असतात. तुम्ही बँकेकडून कधी कर्ज घेतले नसेल, तर तुमचा स्कोर कदाचित असणारच नाही."],
    "GhostScore instead reads regular payments such as electricity bills, rent and UPI. In this demo build the model is a baseline trained on public Taiwan 2009 credit-card data, and the document fields are mapped to its inputs by a heuristic. It has not been validated on Indian borrowers.": ["GhostScore इसके बजाय बिजली बिल, किराया और UPI जैसे नियमित भुगतान पढ़ता है। इस डेमो संस्करण में मॉडल सार्वजनिक ताइवान 2009 क्रेडिट-कार्ड डेटा पर प्रशिक्षित एक बुनियादी मॉडल है, और दस्तावेज़ के फ़ील्ड एक अनुमानित नियम से उसके इनपुट से जोड़े गए हैं। भारतीय कर्ज़दारों पर इसे जाँचा नहीं गया है।", "GhostScore त्याऐवजी वीज बिल, भाडे आणि UPI सारखी नियमित पेमेंट वाचते. या डेमो आवृत्तीत मॉडेल हे सार्वजनिक तैवान 2009 क्रेडिट-कार्ड डेटावर प्रशिक्षित मूलभूत मॉडेल आहे, आणि कागदपत्रांतील फील्ड अंदाजी नियमाने त्याच्या इनपुटशी जोडली आहेत. भारतीय कर्जदारांवर त्याची पडताळणी केलेली नाही."],
    "Document Vault Status": ["दस्तावेज़ वॉल्ट की स्थिति", "कागदपत्र वॉल्ट स्थिती"],
    "{n} of {m} added": ["{m} में से {n} जोड़े", "{m} पैकी {n} जोडले"],
    "Added": ["जोड़ा गया", "जोडले"],
    "Manage documents": ["दस्तावेज़ प्रबंधित करें", "कागदपत्रे व्यवस्थापित करा"],
    "Ask Mitra": ["मित्र से पूछें", "मित्रला विचारा"],
    "Credit coach (demo replies in local mode)": ["क्रेडिट कोच (लोकल मोड में डेमो उत्तर)", "क्रेडिट कोच (लोकल मोडमध्ये डेमो उत्तरे)"],
    "Ask simple questions in Marathi, Hindi, or English.": ["हिंदी, मराठी या अंग्रेज़ी में सरल सवाल पूछें।", "मराठी, हिंदी किंवा इंग्रजीत सोपे प्रश्न विचारा."],
    "Type your question…": ["अपना सवाल लिखें…", "तुमचा प्रश्न लिहा…"],
    "Enabling inclusive alternative underwriting for India's grassroots micro-entrepreneurs and gig workers with dignity.": ["भारत के ज़मीनी छोटे उद्यमियों और गिग कामगारों के लिए सम्मान के साथ समावेशी वैकल्पिक क्रेडिट आकलन।", "भारतातील तळागाळातील छोट्या उद्योजकांसाठी आणि गिग कामगारांसाठी सन्मानाने सर्वसमावेशक पर्यायी क्रेडिट मूल्यांकन."],
    "Hackathon demo build. Not a lender and not a registered aggregator. Synthetic personas only.": ["हैकाथॉन डेमो संस्करण। यह कर्जदाता नहीं है और पंजीकृत एग्रीगेटर भी नहीं। सिर्फ़ काल्पनिक व्यक्ति।", "हॅकेथॉन डेमो आवृत्ती. हा कर्जदाता नाही आणि नोंदणीकृत एग्रीगेटरही नाही. फक्त काल्पनिक व्यक्ती."],
    "Loan options (model-based)": ["लोन विकल्प (मॉडल-आधारित)", "कर्ज पर्याय (मॉडेल-आधारित)"],
    "Your band": ["आपकी श्रेणी", "तुमची श्रेणी"],
    "Possible Loan Options": ["संभावित लोन विकल्प", "संभाव्य कर्ज पर्याय"],
    "{n} found": ["{n} मिले", "{n} सापडले"],
    "Drawn from the policy passages shown": ["दिखाए गए नीति-अंशों से लिए गए", "दाखवलेल्या धोरण-उताऱ्यांतून घेतलेले"],
    "What the passage says": ["अंश में क्या लिखा है", "उताऱ्यात काय आहे"],
    "Facts we could not confirm from the documents": ["ऐसी बातें जिनकी पुष्टि दस्तावेज़ों से नहीं हो सकी", "ज्यांची कागदपत्रांतून खात्री करता आली नाही अशा गोष्टी"],
    "No loan options found.": ["कोई लोन विकल्प नहीं मिला।", "कोणताही कर्ज पर्याय सापडला नाही."],
  });
  const LANG_IDX = { hi: 0, mr: 1 };
  const has = (o, k) => Object.prototype.hasOwnProperty.call(o, k);
  function t(k, vars) {
    const i = LANG_IDX[cfg.language];
    let s = (i !== undefined && has(D, k)) ? D[k][i] : k;
    if (vars) Object.keys(vars).forEach(n => { s = s.split("{" + n + "}").join(vars[n]); });
    return s;
  }
  const BAND_TR = {
    hi: { Poor: "शुरुआती", Fair: "ठीक-ठाक", Good: "अच्छा", Excellent: "उत्कृष्ट" },
    mr: { Poor: "सुरुवातीचा", Fair: "बरा", Good: "चांगला", Excellent: "उत्कृष्ट" },
  };
  const NAME_TR = { priya: { hi: "प्रिया", mr: "प्रिया" } };
  const LOCALE = { en: undefined, hi: "hi-IN", mr: "mr-IN" }[cfg.language];
  const LANG_NAMES = { en: "English", hi: "हिंदी", mr: "मराठी" };
  document.documentElement.lang = cfg.language;

  // ── helpers ──────────────────────────────────────────────────────────────
  const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const bandLabel = b => (BAND_TR[cfg.language] && BAND_TR[cfg.language][b]) || (BANDS.find(x => x.api === b) || { label: b }).label;

  async function get(path, params = {}) {
    const u = new URL(API + path);
    Object.entries({ user_id: cfg.userId, language: cfg.language, ...params }).forEach(([k, v]) => u.searchParams.set(k, v));
    const r = await fetch(u);
    if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
    return r.json();
  }
  async function post(path, body) {
    const r = await fetch(API + path, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: cfg.userId, language: cfg.language, ...body }),
    });
    if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
    return r.json();
  }
  async function upload(blob, filename, docType) {
    const fd = new FormData();
    fd.append("file", blob, filename);
    fd.append("doc_type", docType);
    fd.append("user_id", cfg.userId);
    const r = await fetch(API + "/documents", { method: "POST", body: fd });
    if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
    return r.json();
  }

  // Wide viewports use the desktop (website) layout for the score and loan-option screens.
  const WIDE = () => window.innerWidth >= 1280;
  function go(key) {
    if (WIDE() && key === "score") key = "dash";
    if (WIDE() && key === "options") key = "dloans";
    window.location.href = `../${SCREENS[key]}/code.html`;
  }
  const mainRoot = () => document.querySelector("main > div") || document.querySelector("main");

  const CARD = "bg-surface-container-lowest rounded-xl p-space-md shadow-sm";
  const BTN  = "w-full min-h-[48px] bg-primary text-on-primary rounded-lg font-label-lg text-label-lg flex items-center justify-center gap-2 shadow-sm";
  const BTN2 = "w-full min-h-[48px] bg-surface-container-low text-primary rounded-lg font-label-md text-label-md flex items-center justify-center gap-2";
  const NOTE = `<div class="bg-surface-container-low rounded-xl p-space-md flex items-start gap-space-sm"><span class="material-symbols-outlined text-primary text-[20px] flex-shrink-0 mt-0.5">info</span><p class="font-label-sm text-label-sm text-on-surface leading-normal">`;

  function disclaimer(text) {
    return `${NOTE}<strong>${esc(t("Model estimate, not a lender decision."))}</strong>${text ? " " + esc(t(text)) : ""} ` +
           `${esc(t("Demo build: trained on public Taiwan 2009 credit-card data and run on synthetic personas. No India-validated accuracy is claimed."))}</p></div>`;
  }
  function empty(msg, btnText, target) {
    return `<div class="${CARD} flex flex-col gap-space-md"><p class="font-body-md text-on-surface">${esc(t(msg))}</p>` +
           `<button type="button" data-go="${target}" class="${BTN}">${esc(t(btnText))}</button></div>`;
  }
  function bindGo(root) {
    root.querySelectorAll("[data-go]").forEach(b => b.addEventListener("click", () => go(b.dataset.go)));
  }

  // ── shared chrome: bottom nav, language buttons ──────────────────────────
  function bindChrome() {
    const map = { home: "welcome", documents: "upload", score: "score", advisor: "chat",
      "overview-home": "score", "document-vault": "upload", "credit-score-journey": "history",
      "loan-options": "options", "improvement-plan": "plan", "advisor-ai": "chat", "audit-compliance": "audit" };
    document.querySelectorAll("nav a[data-path]").forEach(a => {
      const k = map[a.dataset.path];
      if (k) a.addEventListener("click", e => { e.preventDefault(); go(k); });
    });
    const langs = { "EN": "en", "हिं": "hi", "म": "mr" };
    const btns = {};
    document.querySelectorAll("button").forEach(b => { const l = langs[b.textContent.trim()]; if (l && !b.hasAttribute("onclick")) btns[l] = b; });
    if (btns.en && btns.hi && btns.mr) {
      // Stitch markup differs per screen: reuse the screen's own active/inactive classes.
      const activeCls = btns.en.className, inactiveCls = btns.hi.className;
      Object.entries(btns).forEach(([l, b]) => {
        const on = l === cfg.language;
        b.className = on ? activeCls : inactiveCls;
        b.setAttribute("aria-pressed", on ? "true" : "false");
        b.setAttribute("aria-label", on ? `${LANG_NAMES[l]} (selected)` : LANG_NAMES[l]);
        b.addEventListener("click", () => setLang(l));
      });
    }
    // Chat screen has its own compact badge: make it cycle EN -> हिं -> म.
    document.querySelectorAll("button[onclick*='toggleLangBadge']").forEach(b => {
      const short = { en: "EN", hi: "हिं", mr: "म" };
      const next = { en: "hi", hi: "mr", mr: "en" };
      b.removeAttribute("onclick");
      b.textContent = short[cfg.language];
      b.setAttribute("aria-label", LANG_NAMES[next[cfg.language]]);
      b.addEventListener("click", () => setLang(next[cfg.language]));
    });
  }
  function setLang(l) {
    if (l === cfg.language) return;
    store.set("lang", l);
    // Cached results were generated in the previous language: drop them so they are re-fetched.
    store.set("score", null); store.set("plan", null);
    window.location.reload();
  }
  // Translate static Stitch text nodes (exact English match against the dictionary).
  function translateStatic() {
    if (!LANG_IDX.hasOwnProperty(cfg.language)) return;
    const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    const nodes = []; while (w.nextNode()) nodes.push(w.currentNode);
    nodes.forEach(n => {
      const raw = n.nodeValue.replace(/\s+/g, " ").trim();
      if (raw && has(D, raw)) n.nodeValue = n.nodeValue.replace(n.nodeValue.trim(), t(raw));
    });
    document.querySelectorAll("[aria-label]").forEach(e => {
      const a = e.getAttribute("aria-label"); if (a && has(D, a)) e.setAttribute("aria-label", t(a));
    });
    const inp = document.getElementById("userInput");
    if (inp) inp.placeholder = ({ en: "Ask in English, हिंदी, मराठी...", hi: "हिंदी, मराठी या अंग्रेज़ी में पूछें...", mr: "मराठी, हिंदी किंवा इंग्रजीत विचारा..." })[cfg.language];
  }

  // ── Welcome ──────────────────────────────────────────────────────────────
  function initWelcome() {
    document.querySelectorAll("button").forEach(b => {
      if (/Continue to Build/i.test(b.textContent)) b.addEventListener("click", () => go("upload"));
      if (/Delete my data/i.test(b.textContent)) {
        b.removeAttribute("onclick");
        b.addEventListener("click", () => alert(t("Demo build: data is held in server memory only and is cleared on restart. No delete-account flow is implemented yet.")));
      }
    });
    // Remove sample claims that this build cannot back up
    document.querySelectorAll("span").forEach(s => {
      const tx = s.textContent.trim();
      if (/Trusted by .* entrepreneurs/i.test(tx)) s.closest("div")?.remove();
      if (/auto-deleted after 180 days/i.test(tx)) s.closest("div")?.remove();
      if (/Compliant with RBI/i.test(tx)) s.parentElement?.remove();
    });
  }

  // ── Upload ───────────────────────────────────────────────────────────────
  function initUpload() {
    const root = mainRoot();
    const docs = store.get("docs", []);
    const cards = DOC_TYPES.map(d => {
      const mine = docs.filter(x => x.doc_type === d.type);
      return `<div class="${CARD} flex flex-col gap-space-sm" data-doc-type="${d.type}">
        <div class="flex items-start justify-between gap-space-xs">
          <div class="flex items-center gap-space-sm">
            <div class="w-11 h-11 rounded-lg bg-surface-container flex items-center justify-center text-primary shrink-0"><span class="material-symbols-outlined text-[26px]">${d.icon}</span></div>
            <div><h2 class="font-headline-sm text-headline-sm text-on-surface">${esc(t(d.label))}</h2><p class="font-body-sm text-body-sm text-on-surface-variant" data-msg>${mine.length ? esc(mine[mine.length - 1].filename) : esc(t(d.hint))}</p></div>
          </div>
          <span data-badge class="px-2.5 py-1 rounded-full font-label-sm text-label-sm font-semibold shrink-0 ${mine.length ? "bg-emerald-100 text-emerald-800" : "bg-surface-container text-on-surface-variant"}">${mine.length ? t("Added ({n})", { n: mine.length }) : t("Not added")}</span>
        </div>
        <div class="flex items-center gap-space-sm">
          <button type="button" data-pick class="flex-1 min-h-[48px] rounded-lg bg-primary/10 text-primary font-label-md text-label-md flex items-center justify-center gap-1.5"><span class="material-symbols-outlined text-[18px]">folder_open</span>${t("Choose file")}</button>
          <button type="button" data-sample class="flex-1 min-h-[48px] rounded-lg bg-surface-container-low text-primary font-label-md text-label-md flex items-center justify-center gap-1.5"><span class="material-symbols-outlined text-[18px]">science</span>${t("Use sample")}</button>
          <input type="file" accept="image/*,application/pdf" class="hidden" data-file>
        </div></div>`;
    }).join("");

    root.innerHTML = `
      <div class="flex flex-col gap-space-xs pt-space-sm">
        <h1 class="font-headline-lg-mobile text-headline-lg-mobile text-on-surface">${t("Upload Payment Records")}</h1>
        <p class="font-body-md text-body-md text-on-surface-variant">${t("Every regular payment adds to your picture. Add what you have.")}</p>
      </div>
      ${NOTE}<strong>${t("Demo build:")}</strong> ${t("Document extraction is a labelled stub in local mode. It returns sample fields for the document type and does not read your file. \"Use sample\" uploads a placeholder file.")}</p></div>
      <div class="flex flex-col gap-space-md" id="gs-cards">${cards}</div>
      <p class="font-body-sm text-on-surface-variant" id="gs-count">${t("{n} document(s) added", { n: docs.length })}</p>
      <button type="button" id="gs-continue" class="${BTN}">${t("Review added documents")} <span class="material-symbols-outlined text-[20px]">arrow_forward</span></button>`;

    root.querySelectorAll("[data-doc-type]").forEach(card => {
      const type = card.dataset.docType;
      const input = card.querySelector("[data-file]");
      const msg = card.querySelector("[data-msg]");
      const badge = card.querySelector("[data-badge]");
      async function send(blob, name) {
        badge.textContent = t("Uploading…");
        try {
          const r = await upload(blob, name, type);
          const all = store.get("docs", []); all.push(r); store.set("docs", all);
          badge.textContent = t("Added ({n})", { n: all.filter(x => x.doc_type === type).length });
          badge.className = "px-2.5 py-1 rounded-full font-label-sm text-label-sm font-semibold shrink-0 bg-emerald-100 text-emerald-800";
          msg.textContent = name;
          root.querySelector("#gs-count").textContent = t("{n} document(s) added", { n: all.length });
        } catch (e) { badge.textContent = t("Error"); msg.textContent = e.message; }
      }
      card.querySelector("[data-pick]").addEventListener("click", () => input.click());
      input.addEventListener("change", () => input.files[0] && send(input.files[0], input.files[0].name));
      card.querySelector("[data-sample]").addEventListener("click", () =>
        send(new Blob(["GhostScore demo placeholder document"], { type: "text/plain" }), `sample_${type}.txt`));
    });
    root.querySelector("#gs-continue").addEventListener("click", () => {
      if (!store.get("docs", []).length) { alert(t("Add at least one document first.")); return; }
      go("review");
    });
  }

  // ── Review ───────────────────────────────────────────────────────────────
  async function initReview() {
    const root = mainRoot();
    const docs = store.get("docs", []);
    if (!docs.length) { root.innerHTML = empty("No documents added yet.", "Add documents", "upload"); bindGo(root); return; }
    root.innerHTML = `<div class="pt-space-sm"><h1 class="font-headline-lg-mobile text-headline-lg-mobile text-on-surface">${t("Check your documents")}</h1>
      <p class="font-body-md text-on-surface-variant">${t("Here is what we read from each one.")}</p></div><div id="gs-reviews" class="flex flex-col gap-space-md"></div>
      <button type="button" id="gs-calc" class="${BTN}">${t("Calculate my score")} <span class="material-symbols-outlined text-[20px]">arrow_forward</span></button>
      <button type="button" data-go="upload" class="${BTN2}">${t("Add more documents")}</button>`;
    bindGo(root);
    const list = root.querySelector("#gs-reviews");
    const FIELDS = [["payer_name", t("Name")], ["biller_or_landlord", t("Biller / landlord")], ["amount", t("Amount")], ["due_date", t("Due date")], ["paid_date", t("Paid date")], ["period", t("Period")]];
    for (const d of docs) {
      try {
        const r = await get(`/documents/${d.doc_id}/review`, { declared_name: "Priya Sharma" });
        const color = { accepted: "bg-emerald-100 text-emerald-800", needs_review: "bg-amber-100 text-amber-800" }[r.status] || "bg-red-100 text-red-800";
        const rows = FIELDS.filter(([k]) => r.normalized[k]).map(([k, l]) =>
          `<div class="flex flex-col"><span class="font-label-sm text-on-surface-variant">${l}</span><span class="font-label-md text-on-surface">${esc(k === "amount" ? `${r.normalized.currency || "INR"} ${r.normalized[k]}` : r.normalized[k])}</span></div>`).join("");
        const el = document.createElement("div");
        el.className = `${CARD} flex flex-col gap-space-sm`;
        el.innerHTML = `<div class="flex items-center justify-between"><h2 class="font-headline-sm text-headline-sm">${esc(t((DOC_TYPES.find(x => x.type === d.doc_type) || { label: d.doc_type }).label))}</h2>
          <span class="px-2.5 py-1 rounded-full font-label-sm font-semibold ${color}">${esc(t({ accepted: "Accepted", needs_review: "Needs review" }[r.status] || "Unreadable"))}</span></div>
          <div class="grid grid-cols-2 gap-space-sm">${rows}</div>
          ${r.flags.length ? `<p class="font-body-sm text-amber-700">${esc(r.applicant_message)}</p>` : `<p class="font-body-sm text-on-surface-variant">${esc(r.applicant_message)}</p>`}`;
        list.appendChild(el);
      } catch (e) {
        list.insertAdjacentHTML("beforeend", `<div class="${CARD}"><p class="text-red-700">${esc(t("Could not load review:"))} ${esc(e.message)}</p></div>`);
      }
    }
    const calc = root.querySelector("#gs-calc");
    calc.addEventListener("click", async () => {
      calc.disabled = true; calc.textContent = t("Calculating…");
      try { store.set("score", await post("/score", { doc_ids: docs.map(d => d.doc_id) })); store.set("plan", null); go("score"); }
      catch (e) { alert(t("Score calculation failed:") + " " + e.message); calc.disabled = false; calc.textContent = t("Calculate my score"); }
    });
  }

  // ── Score dashboard ──────────────────────────────────────────────────────
  async function loadScore() {
    let s = store.get("score", null);
    if (!s) { try { s = await get("/score/latest"); store.set("score", s); } catch (e) { return null; } }
    return s;
  }
  function arcPath(score) {
    const p = Math.min(Math.max((score - 300) / 550, 0.001), 0.999);
    const x = 100 - 80 * Math.cos(Math.PI * p), y = 100 - 80 * Math.sin(Math.PI * p);
    return `M 20 100 A 80 80 0 0 1 ${x.toFixed(1)} ${y.toFixed(1)}`;
  }
  function factorCards(list, tone) {
    if (!list || !list.length) return `<p class="font-body-sm text-on-surface-variant">${esc(t("Nothing stands out yet."))}</p>`;
    const col = tone === "good" ? "#15803d" : "#b45309", icon = tone === "good" ? "task_alt" : "warning";
    return list.map(f => `<div class="${CARD} flex items-start gap-space-md"><div class="w-10 h-10 rounded-lg bg-surface-container-high flex-shrink-0 flex items-center justify-center" style="color:${col}"><span class="material-symbols-outlined text-[24px]">${icon}</span></div>
      <div class="flex flex-col flex-1 min-w-0"><div class="flex items-center justify-between gap-2"><h3 class="font-label-lg text-label-lg text-on-surface font-semibold">${esc(f.plain_label || f.feature)}</h3>
      <span class="bg-surface-container-high font-label-sm px-2 py-0.5 rounded font-bold" style="color:${col}">${esc(t("model weight {n}%", { n: Math.round((f.contribution || 0) * 100) }))}</span></div></div></div>`).join("");
  }
  async function initScore() {
    const root = mainRoot();
    const s = await loadScore();
    if (!s) { root.innerHTML = empty("No score yet. Add your documents to get one.", "Add documents", "upload"); bindGo(root); return; }
    const name = (NAME_TR[cfg.userId] && NAME_TR[cfg.userId][cfg.language]) || (cfg.userId.charAt(0).toUpperCase() + cfg.userId.slice(1));
    const grid = BANDS.map(b => {
      const on = b.api === s.band;
      return `<div class="flex flex-col ${on ? "bg-secondary-fixed/50 rounded py-0.5" : ""}"><span class="${on ? "font-bold text-on-surface" : "font-medium text-on-surface-variant"}">${b.range}</span><span class="text-[11px] ${on ? "font-bold" : ""}">${esc(bandLabel(b.api))}${on ? " ●" : ""}</span></div>`;
    }).join("");
    root.innerHTML = `
      <div class="flex flex-col gap-space-xs pt-space-sm">
        <h1 class="font-headline-sm text-headline-sm text-on-surface">${esc(t("Namaste, {name}", { name }))}</h1>
        <p class="font-label-sm text-label-sm text-outline">${t("Synthetic demo persona")}</p>
      </div>
      <div class="bg-surface-container-lowest rounded-xl p-space-lg shadow-sm flex flex-col items-center text-center">
        <div class="w-full flex items-center justify-between font-label-sm text-on-surface-variant mb-space-xs"><span class="font-semibold text-on-surface">${t("Credit Readiness")}</span><span>${t("Model estimate")}</span></div>
        <div class="relative w-56 h-32 flex items-end justify-center my-2" role="meter" aria-label="GhostScore ${s.score} out of 850, band ${esc(bandLabel(s.band))}" aria-valuenow="${s.score}" aria-valuemin="300" aria-valuemax="850">
          <svg class="w-56 h-32 overflow-visible" viewBox="0 0 200 110" aria-hidden="true"><path d="M 20 100 A 80 80 0 0 1 180 100" fill="none" stroke="#eeeeed" stroke-linecap="round" stroke-width="16"/><path d="${arcPath(s.score)}" fill="none" stroke="#0e625b" stroke-linecap="round" stroke-width="16"/></svg>
          <div class="absolute bottom-1 flex flex-col items-center"><span class="font-display text-display text-on-surface font-bold leading-none" id="scoreDisplay">${s.score}</span><span class="font-label-sm text-on-surface-variant font-semibold mt-0.5">${t("out of 850")}</span></div>
        </div>
        <div class="w-full max-w-[280px] grid grid-cols-4 gap-1 mt-1 text-center font-label-sm text-[12px] text-on-surface-variant">${grid}</div>
        <div class="mt-space-sm px-3.5 py-1.5 rounded-full bg-secondary-fixed font-bold text-on-secondary-fixed">${esc(bandLabel(s.band).toUpperCase())}</div>
        <p class="mt-space-sm font-body-sm text-on-surface">${esc(s.headline)}</p>
        <div class="w-full mt-space-md bg-surface-container-low rounded-lg p-space-sm text-left"><p class="font-body-sm text-on-surface">${esc(s.confidence_note)}</p>
          <p class="font-label-sm text-on-surface-variant pt-1">${esc(t("Updated {date}", { date: new Date().toLocaleDateString(LOCALE) }))}</p></div>
      </div>
      <div class="flex flex-col gap-space-sm"><h2 class="font-headline-sm text-headline-sm text-on-surface flex items-center gap-2"><span class="w-2.5 h-2.5 rounded-full bg-[#15803d]"></span>${t("Signals the model leans on most")}</h2>${factorCards(s.what_helped, "good")}</div>
      <div class="flex flex-col gap-space-sm"><h2 class="font-headline-sm text-headline-sm text-on-surface flex items-center gap-2"><span class="w-2.5 h-2.5 rounded-full bg-[#b45309]"></span>${t("Signals the model leans on least")}</h2>${factorCards(s.what_held_back, "bad")}</div>
      <p class="font-label-sm text-on-surface-variant">${esc(t("\"Model weight\" is how much a signal matters to the model for everyone. It is not a personal point value, and this build does not yet compute per-applicant attribution."))}</p>
      <button type="button" data-go="plan" class="${BTN}">${t("See my improvement plan")} <span class="material-symbols-outlined text-[20px]">arrow_forward</span></button>
      <button type="button" data-go="options" class="${BTN2}">${t("Loan options for me")}</button>
      <button type="button" data-go="chat" class="${BTN2}">${t("Ask the advisor")}</button>
      <button type="button" data-go="history" class="${BTN2}">${t("Score history")}</button>
      ${disclaimer("")}`;
    bindGo(root);
  }

  // ── Improvement plan ─────────────────────────────────────────────────────
  async function initPlan() {
    const root = mainRoot();
    const s = await loadScore();
    if (!s) { root.innerHTML = empty("Get a score first to see a plan.", "Add documents", "upload"); bindGo(root); return; }
    let plan = store.get("plan", null);
    if (!plan) { try { plan = await get("/plan"); store.set("plan", plan); } catch (e) { root.innerHTML = `<p>${esc(e.message)}</p>`; return; } }
    const deltaOf = a => parseInt(String(a.expected_change || "").replace(/[^0-9-]/g, ""), 10) || 0;
    const best = Math.max(0, ...plan.actions.map(deltaOf));
    const cards = plan.actions.map((a, i) => `<div class="${CARD} flex flex-col gap-space-sm">
      <div class="flex items-center justify-between"><span class="font-label-sm text-on-surface-variant">${esc(t("Step {n}", { n: i + 1 }))}</span><span class="px-2 py-0.5 rounded-full bg-secondary text-on-secondary font-label-sm">${esc(a.expected_change || "")}</span></div>
      <h3 class="font-headline-sm text-headline-sm text-on-surface">${esc(a.title)}</h3><p class="font-body-sm text-on-surface-variant">${esc(a.why_it_helps)}</p>
      <ol class="list-decimal pl-5 font-body-sm text-on-surface">${(a.steps || []).map(x => `<li>${esc(x)}</li>`).join("")}</ol></div>`).join("");
    root.innerHTML = `<div class="pt-space-sm"><h1 class="font-headline-lg-mobile text-headline-lg-mobile text-on-surface">${t("Your Score Improvement Plan")}</h1>
      <p class="font-body-md text-on-surface-variant">${t("Each estimate below comes from re-scoring your profile with that change. They are not added together.")}</p></div>
      <div class="${CARD} grid grid-cols-2 gap-space-md text-center"><div><p class="font-label-sm text-on-surface-variant">${t("Today")}</p><p class="font-display text-display text-on-surface font-bold">${s.score}</p></div>
      <div><p class="font-label-sm text-on-surface-variant">${t("Best single step")}</p><p class="font-display text-display text-primary font-bold">${best ? "+" + best : "–"}</p></div></div>
      ${cards ? `<div id="gs-plan-cards" class="flex flex-col gap-space-md">${cards}</div>` : `<p class="font-body-md">${t("No improvement steps available right now.")}</p>`}
      <button type="button" data-go="upload" class="${BTN}">${t("Add more documents")}</button>
      ${disclaimer("Point changes are model re-score estimates, not guarantees.")}`;
    bindGo(root);
  }

  // ── Loan options ─────────────────────────────────────────────────────────
  async function initOptions() {
    const root = mainRoot();
    const s = await loadScore();
    let o;
    try { o = await get("/options"); } catch (e) { root.innerHTML = `<p>${esc(e.message)}</p>`; return; }
    const prods = o.products.map(p => `<div class="${CARD} flex flex-col gap-space-xs">
      <span class="self-start px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 font-label-sm font-semibold">${t("May be eligible")}</span>
      <h3 class="font-headline-sm text-headline-sm text-on-surface">${esc(p.name)}</h3><p class="font-body-sm text-on-surface">${esc(p.why_it_may_fit)}</p>
      <p class="font-body-sm text-on-surface-variant">${esc(p.limits_from_passage)}</p>
      <p class="font-label-sm text-on-surface-variant">${t("Source passages:")} ${esc((p.citations || []).join(", "))}</p></div>`).join("");
    const cannot = (o.cannot_confirm || []).map(c => `<li>${esc(c)}</li>`).join("");
    root.innerHTML = `<div class="pt-space-sm"><h1 class="font-headline-lg-mobile text-headline-lg-mobile text-on-surface">${t("Loan Options for You")}</h1>
      <p class="font-body-md text-on-surface-variant">${s ? esc(t("Based on your {band} band ({score}).", { band: bandLabel(s.band), score: s.score })) : t("No score yet, so showing general options.")} ${t("Checking here does not affect any credit profile.")}</p></div>
      ${prods || ""}
      ${cannot ? `<div class="${CARD}"><h2 class="font-headline-sm">${t("Cannot confirm yet")}</h2><ul class="list-disc pl-5 font-body-sm text-on-surface">${cannot}</ul></div>` : ""}
      ${NOTE}${t("Only a regulated lender can decide on a loan. These are possibilities drawn from the policy passages shown (local mode uses a small labelled stub set, not live Vertex AI Search).")}</p></div>`;
  }

  // ── Chat ─────────────────────────────────────────────────────────────────
  async function initChat() {
    const stream = document.getElementById("chatStream");
    const input = document.getElementById("userInput");
    if (!stream || !input) return;
    const s = await loadScore();
    // Replace sample conversation and sample score in the banner
    stream.innerHTML = "";
    document.querySelectorAll("main span").forEach(sp => {
      const t = sp.textContent.trim();
      if (t === "648") sp.textContent = s ? s.score : "–";
      if (t === "Fair" && sp.closest("main > div > div")) sp.textContent = s ? bandLabel(s.band) : "–";
    });
    function bubble(role, text) {
      const w = document.createElement("div");
      w.className = role === "user" ? "flex flex-col items-end max-w-[88%] self-end" : "flex items-start gap-space-sm max-w-[94%]";
      const p = document.createElement("p");
      p.className = "font-body-md text-body-md leading-relaxed whitespace-pre-wrap";
      p.textContent = text;
      const b = document.createElement("div");
      b.className = (role === "user" ? "bg-secondary-fixed text-on-secondary-fixed" : "bg-surface-container-lowest text-on-surface shadow-sm") + " p-space-md rounded-2xl";
      b.appendChild(p); w.appendChild(b); stream.appendChild(w);
      window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" });
    }
    bubble("bot", t("Hello, I am your GhostScore advisor. I can explain your band, what-if estimates and loan options. I do not make credit decisions."));
    window.sendUserMessage = async function () {
      const msg = input.value.trim();
      if (!msg) return;
      input.value = ""; bubble("user", msg);
      try {
        const r = await post("/chat", { message: msg });
        bubble("bot", r.reply);
      } catch (e) { bubble("bot", t("Sorry, something went wrong:") + " " + e.message); }
    };
  }

  // ── History ──────────────────────────────────────────────────────────────
  async function initHistory() {
    const root = mainRoot();
    root.className = "px-margin pt-space-sm flex flex-col gap-space-md w-full";
    let h;
    try { h = await get("/history"); } catch (e) { root.innerHTML = `<p>${esc(e.message)}</p>`; return; }
    const rows = h.entries.slice().reverse().map(e => `<div class="${CARD} flex items-center justify-between"><div><p class="font-label-md text-on-surface">${esc(e.event === "score_computed" || !e.event ? t("Score computed") : e.event)}</p>
      <p class="font-label-sm text-on-surface-variant">${esc(new Date(e.timestamp).toLocaleString(LOCALE))}</p></div>
      <div class="text-right"><p class="font-headline-sm font-bold">${e.score}</p><p class="font-label-sm text-on-surface-variant">${esc(bandLabel(e.band))}</p></div></div>`).join("");
    root.innerHTML = `<div class="pt-space-sm"><h1 class="font-headline-lg-mobile text-headline-lg-mobile text-on-surface">${t("Score history")}</h1></div>
      ${rows || empty("No score history yet.", "Add documents", "upload")}<button type="button" data-go="score" class="${BTN2}">${t("Back to score")}</button>`;
    bindGo(root);
  }

  // ── Audit (judges view) ──────────────────────────────────────────────────
  async function initAudit() {
    const root = mainRoot();
    root.className = "px-margin pt-space-sm flex flex-col gap-space-md w-full";
    let a;
    try { a = await get("/audit"); } catch (e) { root.innerHTML = `<p>${esc(e.message)}</p>`; return; }
    const rows = a.entries.slice().reverse().map(e => `<tr class="border-t border-outline-variant"><td class="p-2">${esc(new Date(e.timestamp).toLocaleString(LOCALE))}</td><td class="p-2">${esc(e.event_type)}</td>
      <td class="p-2">${esc(bandLabel(e.band))}</td><td class="p-2">${esc((e.top_factors || []).join(", "))}</td><td class="p-2">${esc(e.model_version)}</td><td class="p-2">${esc(e.explanation_id)}</td></tr>`).join("");
    root.innerHTML = `<div class="pt-space-sm"><h1 class="font-headline-lg-mobile text-headline-lg-mobile text-on-surface">${t("Audit trail")}</h1>
      <p class="font-body-md text-on-surface-variant">${t("Every score is logged with model version, band and top factors.")}</p></div>
      <div class="${CARD} overflow-x-auto"><table class="w-full text-left font-label-sm"><thead><tr><th class="p-2">${t("Time")}</th><th class="p-2">${t("Event")}</th><th class="p-2">${t("Band")}</th><th class="p-2">${t("Top factors")}</th><th class="p-2">${t("Model")}</th><th class="p-2">${t("Explanation id")}</th></tr></thead>
      <tbody>${rows || `<tr><td class="p-2" colspan="6">${t("No scores logged yet.")}</td></tr>`}</tbody></table></div>
      ${NOTE}${t("Fairness / demographic-parity metrics are not computed in this build, so none are shown.")}</p></div>`;
  }

  // ── Desktop (website) layout ─────────────────────────────────────────────
  // Stitch desktop screens: same approach as mobile. Keep the Stitch header, tokens
  // and card styling; render the content from the live API; drop sample claims
  // (revenue, NBFC partners, "Certified Partner", LSP registry, 35/30/35 weights).
  function desktopChrome() {
    const spans = document.querySelectorAll("header .sm\\:flex span");
    if (spans[0]) spans[0].textContent = (NAME_TR[cfg.userId] && NAME_TR[cfg.userId][cfg.language]) || (cfg.userId.charAt(0).toUpperCase() + cfg.userId.slice(1));
    if (spans[1]) spans[1].textContent = t("Synthetic demo persona");
    document.querySelectorAll("header [aria-label='Notifications']").forEach(b => b.remove());
    const f = document.querySelector("footer");
    if (f) {
      f.querySelectorAll("a[data-path]").forEach(a => a.remove());
      f.querySelectorAll("p").forEach(p => { if (/Certified Partner/i.test(p.textContent)) p.textContent = t("Hackathon demo build. Not a lender and not a registered aggregator. Synthetic personas only."); });
    }
  }
  const CHIP = "px-3 py-1.5 rounded-full bg-surface-container-high text-on-surface-variant font-label-sm text-label-sm hover:text-on-surface transition-colors";
  function dFactor(f, tone) {
    const good = tone === "good";
    return `<div class="p-space-sm rounded-lg bg-surface-container-low flex items-start gap-space-sm"><span class="material-symbols-outlined ${good ? "text-primary" : "text-secondary"} text-[20px] mt-0.5">${good ? "task_alt" : "warning"}</span>
      <div class="flex flex-col"><span class="font-label-md text-label-md text-on-surface font-semibold">${esc(f.plain_label || f.feature)}</span>
      <span class="font-label-sm text-[11px] ${good ? "text-primary" : "text-secondary"} font-semibold mt-1">${esc(t("model weight {n}%", { n: Math.round((f.contribution || 0) * 100) }))}</span></div></div>`;
  }
  function dGauge(score) {
    const p = Math.min(Math.max((score - 300) / 550, 0.001), 0.999);
    const x = 120 - 100 * Math.cos(Math.PI * p), y = 120 - 100 * Math.sin(Math.PI * p);
    return `<svg aria-hidden="true" class="w-64 h-36" viewBox="0 0 240 135"><path d="M 20 120 A 100 100 0 0 1 220 120" fill="none" stroke="#e2e2e2" stroke-linecap="round" stroke-width="22"/>
      <path d="M 20 120 A 100 100 0 0 1 ${x.toFixed(1)} ${y.toFixed(1)}" fill="none" stroke="#004943" stroke-linecap="round" stroke-width="22"/>
      <circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" fill="#004943" r="7" stroke="#ffffff" stroke-width="3"/></svg>`;
  }
  const DWRAP = "max-w-7xl mx-auto w-full px-margin-desktop py-space-xl flex flex-col gap-space-xl";
  const DCARD = "bg-surface-container-lowest rounded-xl shadow-sm p-space-lg flex flex-col gap-space-md";
  const DBTN = "inline-flex items-center justify-center gap-space-xs px-space-lg py-3 rounded-lg bg-primary text-on-primary font-label-md text-label-md font-bold hover:bg-primary-container transition-colors shadow-sm";

  async function initDash() {
    desktopChrome();
    const main = document.querySelector("main");
    const s = await loadScore();
    if (!s) { main.innerHTML = `<div class="${DWRAP}">${empty("No score yet. Add your documents to get one.", "Add documents", "upload")}</div>`; bindGo(main); return; }
    let plan = store.get("plan", null);
    if (!plan) { try { plan = await get("/plan"); store.set("plan", plan); } catch (e) { plan = { actions: [] }; } }
    let opts = { products: [] };
    try { opts = await get("/options"); } catch (e) { /* shown as 0 */ }
    const docs = store.get("docs", []);
    const types = DOC_TYPES.filter(d => docs.some(x => x.doc_type === d.type));
    const name = (NAME_TR[cfg.userId] && NAME_TR[cfg.userId][cfg.language]) || (cfg.userId.charAt(0).toUpperCase() + cfg.userId.slice(1));
    const deltaOf = a => parseInt(String(a.expected_change || "").replace(/[^0-9-]/g, ""), 10) || 0;
    const best = (plan.actions || []).slice().sort((a, b) => deltaOf(b) - deltaOf(a))[0];
    const conf = Math.round((s.band_confidence || 0) * 100);
    const legend = BANDS.map(b => {
      const on = b.api === s.band;
      return `<div class="p-2 rounded ${on ? "bg-secondary-fixed/30" : "bg-surface-container-low opacity-80"} flex flex-col"><span class="font-label-sm text-label-sm ${on ? "text-on-secondary-fixed font-bold" : "text-on-surface-variant"}">${esc(on ? t("{band} (You)", { band: bandLabel(b.api) }) : bandLabel(b.api))}</span><span class="font-label-sm text-[11px] ${on ? "text-secondary font-bold" : "text-outline font-semibold"}">${b.range.replace("-", " – ")}</span></div>`;
    }).join("");
    const vault = DOC_TYPES.map(d => {
      const n = docs.filter(x => x.doc_type === d.type).length;
      return `<div class="flex items-center justify-between text-body-sm font-body-sm py-1"><span class="flex items-center gap-2 ${n ? "text-on-surface" : "text-on-surface-variant"}"><span class="material-symbols-outlined ${n ? "text-primary" : "text-secondary"} text-[18px]">${n ? "check_circle" : "pending"}</span>${esc(t(d.label))}</span>
        <span class="${n ? "text-primary" : "text-secondary"} font-label-sm text-label-sm font-bold">${esc(n ? t("Added") : t("Not added"))}</span></div>`;
    }).join("");
    const stat = (label, icon, val, sub, hi) => `<div class="${hi ? "bg-primary-fixed/20" : "bg-surface-container-low"} rounded-lg p-space-md flex flex-col justify-between"><div class="flex items-center justify-between text-on-surface-variant mb-1"><span class="font-label-sm text-label-sm uppercase tracking-wider">${esc(label)}</span><span class="material-symbols-outlined text-[18px] text-primary">${icon}</span></div><span class="font-headline-sm text-headline-sm ${hi ? "text-primary" : "text-on-surface"} font-bold">${esc(val)}</span><span class="font-label-sm text-label-sm ${hi ? "text-primary font-semibold" : "text-on-surface-variant"} mt-1">${esc(sub)}</span></div>`;
    main.innerHTML = `<div class="flex flex-col w-full"><div class="${DWRAP}">
      <div class="bg-surface-container-lowest rounded-xl shadow-sm p-space-lg flex flex-col gap-space-lg">
        <div class="flex items-start gap-space-md"><div class="w-16 h-16 rounded-xl bg-primary-fixed flex items-center justify-center flex-shrink-0 text-primary shadow-sm"><span class="material-symbols-outlined text-[36px]">storefront</span></div>
          <div class="flex flex-col gap-space-xs"><div class="flex flex-wrap items-center gap-space-sm"><span class="font-headline-md text-headline-md text-on-surface font-bold tracking-tight">${esc(t("Namaste, {name}", { name }))}</span>
            <span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-surface-container-high text-on-surface-variant text-label-sm font-label-sm">${esc(t("Synthetic demo persona"))}</span></div>
            <p class="font-body-md text-body-md text-on-surface-variant">${esc(t("Demo profile: documents are placeholders in local mode."))}</p></div></div>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-space-md pt-space-xs">
          ${stat(t("Band"), "speed", bandLabel(s.band), `${s.score} / 850`)}
          ${stat(t("Documents Added"), "receipt_long", String(docs.length), t("{n} of {m} types", { n: types.length, m: DOC_TYPES.length }))}
          ${stat(t("Model Confidence"), "verified_user", conf + "%", t("Model estimate"))}
          ${stat(t("Loan Options"), "local_offer", t("{n} possible", { n: opts.products.length }), t("See details →"), true)}
        </div></div>
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-space-xl items-start">
        <div class="lg:col-span-7 flex flex-col gap-space-xl">
          <div class="${DCARD}">
            <div class="flex items-center justify-between gap-space-sm"><div class="flex flex-col"><span class="font-headline-sm text-headline-sm text-on-surface font-bold">${esc(t("GhostScore Alternative Index"))}</span><span class="font-body-sm text-body-sm text-on-surface-variant">${esc(t("Estimated from the payment documents you added"))}</span></div>
              <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-primary/10 text-primary font-label-sm text-label-sm font-semibold">${esc(t("Model confidence {n}%", { n: conf }))}</span></div>
            <div class="flex flex-col md:flex-row items-center justify-around gap-space-lg py-space-sm">
              <div class="relative w-64 h-36 flex items-end justify-center" role="meter" aria-label="GhostScore ${s.score} / 850" aria-valuenow="${s.score}" aria-valuemin="300" aria-valuemax="850">${dGauge(s.score)}
                <div class="absolute bottom-0 flex flex-col items-center"><span id="scoreDisplay" class="font-display text-display text-on-surface font-bold leading-none tracking-tight">${s.score}</span><span class="font-label-sm text-label-sm text-on-surface-variant font-medium mt-1">${esc(t("out of 850"))}</span></div></div>
              <div class="flex flex-col gap-space-sm max-w-xs text-center md:text-left">
                <div class="inline-flex items-center gap-2 self-center md:self-start px-3 py-1 rounded-lg bg-secondary-fixed/50 text-on-secondary-fixed font-label-md text-label-md font-bold"><span class="material-symbols-outlined text-[18px]">trending_up</span>${esc(bandLabel(s.band))}</div>
                <p class="font-body-sm text-body-sm text-on-surface-variant">${esc(s.headline)}</p>
                <p class="font-body-sm text-body-sm text-on-surface-variant">${esc(s.confidence_note)}</p></div></div>
            <div class="grid grid-cols-4 gap-space-xs pt-space-xs text-center">${legend}</div></div>
          <div class="bg-gradient-to-r from-primary to-primary-container rounded-xl shadow-md p-space-lg text-on-primary flex flex-col md:flex-row items-center justify-between gap-space-lg">
            <div class="flex flex-col gap-space-xs"><div class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-primary-fixed text-on-primary-fixed font-label-sm text-label-sm font-bold w-max">${esc(t("Possibilities, not approvals"))}</div>
              <h3 class="font-headline-sm text-headline-sm text-on-primary font-bold">${esc(t("{n} possible loan options", { n: opts.products.length }))}</h3>
              <p class="font-body-sm text-body-sm text-on-primary-container max-w-lg">${esc(t("These come from the policy passages shown, not from an approval. Only a regulated lender can decide."))}</p></div>
            <button type="button" data-go="options" class="flex-shrink-0 inline-flex items-center justify-center gap-space-xs px-space-lg py-3 rounded-lg bg-secondary-container text-on-secondary-container hover:bg-secondary-fixed transition-colors font-label-lg text-label-lg font-bold shadow-md"><span>${esc(t("Explore loan options"))}</span><span class="material-symbols-outlined text-[20px]">arrow_forward</span></button></div>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-space-md">
            <div class="bg-surface-container-lowest rounded-xl shadow-sm p-space-md flex flex-col gap-space-sm"><div class="text-primary font-label-md text-label-md font-bold pb-space-xs">${esc(t("Signals the model leans on most"))}</div><div class="flex flex-col gap-space-sm">${(s.what_helped || []).map(f => dFactor(f, "good")).join("") || `<p class="font-body-sm text-on-surface-variant">${esc(t("Nothing stands out yet."))}</p>`}</div></div>
            <div class="bg-surface-container-lowest rounded-xl shadow-sm p-space-md flex flex-col gap-space-sm"><div class="text-secondary font-label-md text-label-md font-bold pb-space-xs">${esc(t("Signals the model leans on least"))}</div><div class="flex flex-col gap-space-sm">${(s.what_held_back || []).map(f => dFactor(f, "bad")).join("") || `<p class="font-body-sm text-on-surface-variant">${esc(t("Nothing stands out yet."))}</p>`}</div></div></div>
          <p class="font-label-sm text-label-sm text-on-surface-variant">${esc(t("\"Model weight\" is how much a signal matters to the model for everyone. It is not a personal point value, and this build does not yet compute per-applicant attribution."))}</p>
          <div class="bg-surface-container-lowest rounded-xl shadow-sm p-space-md"><details class="group cursor-pointer"><summary class="flex items-center justify-between font-label-lg text-label-lg text-on-surface font-bold list-none"><div class="flex items-center gap-space-sm"><span class="material-symbols-outlined text-primary">psychology_alt</span><span>${esc(t("Why this score?"))}</span></div><span class="material-symbols-outlined text-on-surface-variant transition-transform group-open:rotate-180">expand_more</span></summary>
            <div class="pt-space-md flex flex-col gap-space-sm font-body-sm text-body-sm text-on-surface-variant"><p>${esc(t("Traditional bureau scores depend on prior formal loans and credit cards. If you have never borrowed from a bank, you may have no score at all."))}</p><p>${esc(t("GhostScore instead reads regular payments such as electricity bills, rent and UPI. In this demo build the model is a baseline trained on public Taiwan 2009 credit-card data, and the document fields are mapped to its inputs by a heuristic. It has not been validated on Indian borrowers."))}</p></div></details></div>
        </div>
        <div class="lg:col-span-5 flex flex-col gap-space-xl">
          ${best ? `<div class="${DCARD}"><div class="flex items-center justify-between gap-space-sm"><span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-secondary-fixed/60 text-on-secondary-fixed font-label-sm text-label-sm font-bold"><span class="material-symbols-outlined text-[16px]">bolt</span>${esc(t("Best single step"))}: ${esc(best.expected_change || "")}</span></div>
            <div class="flex flex-col gap-space-xs"><h4 class="font-headline-sm text-headline-sm text-on-surface font-bold">${esc(best.title)}</h4><p class="font-body-sm text-body-sm text-on-surface-variant">${esc(best.why_it_helps)}</p></div>
            <button type="button" data-go="plan" class="w-full ${DBTN}">${esc(t("See my improvement plan"))} <span class="material-symbols-outlined text-[18px]">arrow_forward</span></button>
            <p class="font-label-sm text-label-sm text-on-surface-variant">${esc(t("Point changes are model re-score estimates, not guarantees."))}</p></div>` : ""}
          <div class="bg-surface-container-lowest rounded-xl shadow-sm p-space-md flex flex-col gap-space-sm"><div class="flex items-center justify-between"><div class="flex items-center gap-space-xs"><span class="material-symbols-outlined text-primary text-[22px]">folder_managed</span><span class="font-label-lg text-label-lg text-on-surface font-bold">${esc(t("Document Vault Status"))}</span></div><span class="font-label-sm text-label-sm text-on-surface-variant font-semibold">${esc(t("{n} of {m} added", { n: types.length, m: DOC_TYPES.length }))}</span></div>
            <div class="w-full bg-surface-container-high h-2.5 rounded-full overflow-hidden"><div class="bg-primary h-full rounded-full" style="width:${Math.round(100 * types.length / DOC_TYPES.length)}%"></div></div>
            <div class="flex flex-col gap-2 pt-space-xs">${vault}</div>
            <button type="button" data-go="upload" class="text-left text-primary font-label-md text-label-md font-bold hover:underline">${esc(t("Manage documents"))}</button></div>
          <div class="bg-surface-container-lowest rounded-xl shadow-sm p-space-md flex flex-col gap-space-sm"><div class="flex items-center gap-space-sm"><div class="w-9 h-9 rounded-full bg-tertiary-fixed flex items-center justify-center text-tertiary"><span class="material-symbols-outlined text-[20px]">smart_toy</span></div><div class="flex flex-col"><span class="font-label-lg text-label-lg text-on-surface font-bold">${esc(t("Ask Mitra"))}</span><span class="font-label-sm text-label-sm text-on-surface-variant">${esc(t("Credit coach (demo replies in local mode)"))}</span></div></div>
            <p class="font-body-sm text-body-sm text-on-surface-variant">${esc(t("Ask simple questions in Marathi, Hindi, or English."))}</p>
            <div class="flex flex-wrap gap-space-xs" id="gs-chips"><button type="button" class="${CHIP}">${esc(t("What lowers my score?"))}</button><button type="button" class="${CHIP}">${esc(t("What loan fits me?"))}</button></div>
            <div id="gs-reply" class="hidden bg-surface-container-low rounded-lg p-space-sm font-body-sm text-body-sm text-on-surface whitespace-pre-wrap" aria-live="polite"></div>
            <div class="flex items-center gap-space-xs"><input id="gs-ask" type="text" class="flex-1 bg-surface-container-low rounded-lg px-3 py-2.5 font-body-sm text-body-sm outline-none focus:ring-2 focus:ring-primary" placeholder="${esc(t("Type your question…"))}"><button id="gs-send" type="button" aria-label="${esc(t("Send message"))}" class="w-11 h-11 rounded-lg bg-primary text-on-primary flex items-center justify-center"><span class="material-symbols-outlined text-[20px]">send</span></button></div></div>
          ${disclaimer("")}
        </div></div></div></div>`;
    bindGo(main);
    const ask = main.querySelector("#gs-ask"), reply = main.querySelector("#gs-reply");
    async function send() {
      const msg = ask.value.trim(); if (!msg) return;
      reply.classList.remove("hidden"); reply.textContent = "…";
      try { reply.textContent = (await post("/chat", { message: msg })).reply; }
      catch (e) { reply.textContent = t("Sorry, something went wrong:") + " " + e.message; }
    }
    main.querySelector("#gs-send").addEventListener("click", send);
    ask.addEventListener("keydown", e => { if (e.key === "Enter") send(); });
    main.querySelectorAll("#gs-chips button").forEach(b => b.addEventListener("click", () => { ask.value = b.textContent.trim(); send(); }));
  }

  async function initDLoans() {
    desktopChrome();
    const main = document.querySelector("main");
    const s = await loadScore();
    let o;
    try { o = await get("/options"); } catch (e) { main.innerHTML = `<div class="${DWRAP}"><p>${esc(e.message)}</p></div>`; return; }
    const pct = s ? Math.round(100 * Math.min(Math.max((s.score - 300) / 550, 0), 1)) : 0;
    const cards = o.products.map(p => `<div class="flex flex-col justify-between bg-surface-container-lowest rounded-xl p-space-lg shadow-sm hover:shadow-md transition-shadow relative overflow-hidden"><div class="absolute top-0 left-0 right-0 h-1.5 bg-primary"></div>
      <div class="flex flex-col gap-space-md"><div class="flex flex-col gap-space-xs"><div><span class="px-2 py-0.5 rounded bg-secondary-fixed text-on-secondary-fixed font-label-sm text-label-sm font-bold uppercase tracking-wider">${esc(t("May be eligible"))}</span></div>
        <h3 class="font-headline-md text-headline-md text-on-surface font-bold">${esc(p.name)}</h3><p class="font-body-sm text-body-sm text-on-surface-variant">${esc(p.why_it_may_fit)}</p></div>
        <div class="bg-surface-container-low rounded-lg p-space-md flex flex-col gap-1"><span class="font-label-sm text-label-sm text-on-surface-variant">${esc(t("What the passage says"))}</span><span class="font-label-md text-label-md text-on-surface">${esc(p.limits_from_passage)}</span></div>
        <p class="font-label-sm text-label-sm text-on-surface-variant">${esc(t("Source passages:"))} ${esc((p.citations || []).join(", "))}</p></div></div>`).join("");
    const cannot = (o.cannot_confirm || []).map(c => `<li>${esc(c)}</li>`).join("");
    main.innerHTML = `<div class="flex flex-col w-full">
      <div class="relative w-full overflow-hidden bg-surface-container-low px-margin-desktop py-space-xl"><div class="max-w-7xl mx-auto flex flex-col md:flex-row md:items-end justify-between gap-space-md relative z-10">
        <div class="flex flex-col gap-space-xs max-w-3xl"><div><span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-primary-container text-on-primary font-label-sm text-label-sm tracking-wide uppercase">${esc(t("Loan options (model-based)"))}</span></div>
          <h1 class="font-display text-display text-on-surface tracking-tight font-bold">${esc(t("Loan Options for You"))}</h1>
          <p class="font-body-lg text-body-lg text-on-surface-variant leading-relaxed">${s ? esc(t("Based on your {band} band ({score}).", { band: bandLabel(s.band), score: s.score })) : esc(t("No score yet, so showing general options."))} ${esc(t("Checking here does not affect any credit profile."))}</p></div>
        ${s ? `<div class="bg-surface-container-lowest p-space-md rounded-xl shadow-sm flex items-center gap-space-md flex-shrink-0"><div class="relative w-16 h-16 flex items-center justify-center"><svg class="w-full h-full transform -rotate-90" viewBox="0 0 36 36"><path class="text-surface-container-highest" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="currentColor" stroke-width="3.5"/><path class="text-primary-container" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="currentColor" stroke-dasharray="${pct}, 100" stroke-linecap="round" stroke-width="3.5"/></svg><div class="absolute flex flex-col items-center"><span class="font-headline-sm text-headline-sm font-bold text-primary leading-none">${s.score}</span></div></div>
          <div class="flex flex-col"><span class="font-label-sm text-label-sm text-on-surface-variant">${esc(t("Your band"))}</span><span class="font-label-md text-label-md text-on-surface font-semibold">${esc(bandLabel(s.band))}</span></div></div>` : ""}
      </div></div>
      <div class="${DWRAP}"><div class="flex flex-col gap-space-md">
        <div class="flex items-center justify-between"><div class="flex items-center gap-space-sm"><h2 class="font-headline-lg text-headline-lg text-on-surface font-bold tracking-tight">${esc(t("Possible Loan Options"))}</h2><span class="px-2.5 py-0.5 rounded-full bg-primary-fixed text-on-primary-fixed font-label-sm text-label-sm font-semibold">${esc(t("{n} found", { n: o.products.length }))}</span></div>
          <span class="font-label-sm text-label-sm text-on-surface-variant hidden sm:inline-block">${esc(t("Drawn from the policy passages shown"))}</span></div>
        ${cards ? `<div class="grid grid-cols-1 lg:grid-cols-2 gap-space-lg">${cards}</div>` : `<p class="font-body-md">${esc(t("No loan options found."))}</p>`}</div>
        ${cannot ? `<div class="${DCARD}"><h2 class="font-headline-sm text-headline-sm font-bold">${esc(t("Facts we could not confirm from the documents"))}</h2><ul class="list-disc pl-5 font-body-sm text-on-surface">${cannot}</ul></div>` : ""}
        <div class="flex flex-wrap gap-space-sm"><button type="button" data-go="plan" class="${DBTN}">${esc(t("See my improvement plan"))}</button><button type="button" data-go="score" class="${DBTN} !bg-surface-container !text-primary">${esc(t("Back to score"))}</button></div>
        ${NOTE}${esc(t("Only a regulated lender can decide on a loan. These are possibilities drawn from the policy passages shown (local mode uses a small labelled stub set, not live Vertex AI Search)."))}</p></div>
      </div></div>`;
    bindGo(main);
  }

  // ── Desktop shell for the screens that only exist as phone designs ───────
  // The Stitch export has desktop designs for the dashboard and loan options only.
  // For the rest of the flow (welcome, upload, review, plan, chat, history, audit)
  // on a wide window we swap the phone header/bottom-nav for the Stitch desktop
  // header and widen the content. Content and behaviour are unchanged.
  const DESK_NAV = [["overview-home", "Overview / Home"], ["document-vault", "Document Vault"], ["credit-score-journey", "Credit Score & Journey"],
    ["loan-options", "Loan Options"], ["improvement-plan", "Improvement Plan"], ["advisor-ai", "Advisor AI"], ["audit-compliance", "Audit & Compliance"]];
  function deskHeaderHTML(active) {
    const name = (NAME_TR[cfg.userId] && NAME_TR[cfg.userId][cfg.language]) || (cfg.userId.charAt(0).toUpperCase() + cfg.userId.slice(1));
    const on = "transition-colors bg-primary-container text-on-primary font-bold rounded-lg px-3 py-1.5";
    const off = "font-label-md text-label-md text-on-surface-variant hover:text-on-surface transition-colors px-space-xs py-1";
    const nav = DESK_NAV.map(([k, l]) => `<a class="${k === active ? on : off}" ${k === active ? 'aria-current="page"' : ""} data-path="${k}" href="#">${esc(l)}</a>`).join("");
    const lb = "font-label-sm text-label-sm px-2.5 py-1 rounded-full";
    return `<header class="fixed top-0 w-full z-50 bg-surface/90 backdrop-blur-xl shadow-[0_1px_8px_rgba(0,0,0,0.04)]"><div class="h-20 max-w-7xl mx-auto px-margin-desktop flex items-center justify-between gap-space-md">
      <div class="flex flex-col flex-shrink-0"><span class="font-headline-md text-headline-md text-primary tracking-tight font-bold">GhostScore</span><span class="font-label-sm text-label-sm text-on-surface-variant font-medium">Alternative Credit & Advisor</span></div>
      <nav class="hidden xl:flex items-center gap-space-sm">${nav}</nav>
      <div class="flex items-center gap-space-md flex-shrink-0"><div class="flex items-center bg-surface-container-high rounded-full p-0.5">
        <button class="${lb} bg-surface-container-lowest text-primary shadow-sm font-semibold" type="button">EN</button><button class="${lb} text-on-surface-variant hover:text-on-surface transition-colors" type="button">हिं</button><button class="${lb} text-on-surface-variant hover:text-on-surface transition-colors" type="button">म</button></div>
        <div class="flex items-center gap-space-sm pl-space-xs"><div class="flex flex-col text-right hidden sm:flex"><span class="font-label-sm text-label-sm text-on-surface font-semibold leading-tight">${esc(name)}</span><span class="font-label-sm text-[11px] text-on-surface-variant leading-none">Synthetic demo persona</span></div>
        <div class="w-8 h-8 rounded-full bg-primary flex items-center justify-center"><span class="material-symbols-outlined text-on-primary text-[18px]">person</span></div></div></div></div></header>`;
  }
  function desktopShell(p) {
    const table = [["welcome_consent", null, "max-w-6xl"], ["upload_documents", "document-vault", "max-w-6xl"], ["document_check", "document-vault", "max-w-6xl"],
      ["improvement_plan", "improvement-plan", "max-w-6xl"], ["advisor_chat", "advisor-ai", "max-w-3xl"], ["score_trend", "credit-score-journey", "max-w-4xl"],
      ["audit_view", "audit-compliance", "max-w-6xl"]];
    const hit = table.find(x => p.includes(x[0]));
    if (!hit) return false;
    document.querySelector("body > header")?.remove();
    document.querySelector("body > nav")?.remove();
    const main = document.querySelector("main");
    main.classList.remove("max-w-[480px]", "pt-16", "pb-24", "pt-safe", "pb-safe");
    main.classList.add(hit[2], "pt-24", "pb-12");
    const root = main.firstElementChild;   // screens render into main > div: give its children breathing room
    if (root && hit[0] !== "welcome_consent" && hit[0] !== "advisor_chat") root.classList.add("flex", "flex-col", "gap-space-md");
    if (hit[0] === "welcome_consent") main.querySelectorAll("button").forEach(b => { if (/^(EN|हिं|म)$/.test(b.textContent.trim())) b.parentElement.remove(); });
    document.body.insertAdjacentHTML("afterbegin", deskHeaderHTML(hit[1]));
    document.head.insertAdjacentHTML("beforeend", "<style>#gs-cards,#gs-reviews,#gs-plan-cards{display:grid!important;grid-template-columns:repeat(auto-fit,minmax(19rem,1fr));gap:1rem}</style>");
    const bar = document.querySelector("div.fixed.bottom-16");   // chat input bar
    if (bar) { bar.classList.remove("bottom-16", "max-w-[480px]"); bar.classList.add("bottom-0", "max-w-3xl"); }
    return true;
  }
  // Welcome page on a wide window: two columns instead of one phone-width column.
  function desktopWelcome() {
    const main = document.querySelector("main"), inner = main.firstElementChild;
    if (!inner || inner.children.length < 5) return;
    const [langRow, hero, headline, how, rights, cta] = [...inner.children];
    const pill = langRow.firstElementChild;
    [hero, headline, how, rights, cta].forEach(e => e && e.classList.remove("px-margin", "mt-space-md", "mt-space-lg"));
    const h = hero.querySelector(".h-44"); if (h) { h.classList.remove("h-44"); h.classList.add("h-72"); }
    const left = document.createElement("div"), right = document.createElement("div");
    left.className = "flex flex-col gap-space-lg"; right.className = "flex flex-col gap-space-lg";
    if (pill) { pill.classList.add("self-start"); left.append(pill); }
    left.append(headline, hero, how); right.append(rights); if (cta) right.append(cta);
    const grid = document.createElement("div");
    grid.className = "max-w-6xl mx-auto w-full px-margin-desktop py-space-lg grid grid-cols-1 lg:grid-cols-2 gap-space-xl items-start";
    grid.append(left, right);
    inner.replaceChildren(grid);
  }

  // ── boot ─────────────────────────────────────────────────────────────────
  function init() {
    const p = window.location.pathname;
    // Keep the layout in step with the viewport (desktop screens exist for score + loan options).
    const swap = WIDE()
      ? { score_dashboard: "dash", eligible_loan: "dloans" }
      : { desktop_dashboard: "score", desktop_loan: "options" };
    for (const k of Object.keys(swap)) if (p.includes(k)) { window.location.replace(`../${SCREENS[swap[k]]}/code.html`); return; }
    const shelled = WIDE() && !p.includes("desktop_") && desktopShell(p);
    bindChrome();
    if (p.includes("desktop_dashboard")) initDash();
    else if (p.includes("desktop_loan")) initDLoans();
    else if (p.includes("welcome_consent")) { initWelcome(); if (shelled) desktopWelcome(); }
    else if (p.includes("upload_documents")) initUpload();
    else if (p.includes("document_check")) initReview();
    else if (p.includes("score_dashboard")) initScore();
    else if (p.includes("improvement_plan")) initPlan();
    else if (p.includes("advisor_chat")) initChat();
    else if (p.includes("eligible_loan")) initOptions();
    else if (p.includes("score_trend")) initHistory();
    else if (p.includes("audit_view")) initAudit();
    translateStatic();
  }
  window.GhostScore = { go, store };
  document.addEventListener("DOMContentLoaded", init);
})(window);
