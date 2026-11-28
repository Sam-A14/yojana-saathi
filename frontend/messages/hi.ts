// Hindi words for every screen. typed as `typeof en`: a key missing here fails type-check.
//
// needs native review: ALL of this file is a first draft by a non-native speaker. A Hindi speaker
// should read every screen aloud before launch (plain words, no hard Sanskritised terms).
import type { en } from "./en";

export const hi: typeof en = {
  // needs native review
  meta: {
    title: "योजना साथी",
    description: "देखें कि आपके परिवार को कौन-से सरकारी लाभ मिल सकते हैं।",
  },
  // needs native review
  common: {
    appName: "योजना साथी",
    // needs native review
    tagline: "सरकारी योजनाएँ, परिवारों के लिए आसान",
    back: "पीछे",
    next: "आगे बढ़ें",
    cancel: "रद्द करें",
    loading: "लोड हो रहा है…",
    yes: "हाँ",
    no: "नहीं",
    notSure: "पक्का नहीं पता",
    retry: "फिर कोशिश करें",
    choose: "चुनें…",
    waking: "सर्वर को जगाया जा रहा है। पहली बार में एक मिनट तक लग सकता है।",
  },
  language: { label: "भाषा", en: "English", hi: "हिन्दी" },
  // needs native review (new: every line in nav)
  nav: {
    label: "मुख्य मेनू",
    home: "मुख्य पृष्ठ",
    schemes: "योजनाएँ",
    howItWorks: "यह कैसे काम करता है",
    faq: "सवाल-जवाब",
    about: "हमारे बारे में",
    menu: "मेनू",
    closeMenu: "मेनू बंद करें",
    signIn: "साइन इन",
    myFamily: "मेरा परिवार",
    signOut: "साइन आउट",
  },
  // needs native review (independent, github, photoCredit are new)
  footer: {
    disclaimer: "यह केवल जानकारी है, सरकारी निर्णय नहीं। यह सरकारी ऐप नहीं है।",
    noAadhaar: "हम आधार नंबर कभी नहीं माँगते।",
    independent: "योजना साथी एक स्वतंत्र विद्यार्थी प्रोजेक्ट है, सरकारी वेबसाइट नहीं।",
    github: "कोड GitHub पर",
    photoCredit: "फ़ोटो: the Amritdev / Pexels",
  },
  // needs native review
  errors: {
    network:
      "सर्वर से संपर्क नहीं हो पाया। इंटरनेट देखें और फिर कोशिश करें। पहली बार में एक मिनट तक लग सकता है।",
    // needs native review (owner): timeout
    timeout: "सहेजने में बहुत समय लग रहा है। आपके जवाब यहीं हैं। फिर से कोशिश करें।",
    signedOut: "आपका साइन-इन खत्म हो गया है। कृपया फिर से साइन इन करें।",
    denied: "हम यह परिवार नहीं खोल पाए। कृपया फिर से साइन इन करें।",
    limit: "आप इससे ज़्यादा लोग नहीं जोड़ सकते।",
    generic: "हमारी तरफ़ से कुछ गड़बड़ हो गई। कृपया फिर कोशिश करें।",
  },
  // needs native review
  home: {
    title: "वे लाभ खोजिए जिनके आपका परिवार हक़दार है।",
    intro:
      "अपने परिवार के बारे में एक बार बताइए। हम बताएँगे कि हर सदस्य किन सरकारी योजनाओं के लिए पात्र हो सकता है और कौन-से कागज़ अभी चाहिए।",
    start: "मेरे परिवार के लिए योजनाएँ खोजें",
    // needs native review (changed in the Google sign-in change: no longer says "with email")
    signIn: "साइन इन करें",
    example: "डेमो परिवार आज़माएँ",
    free: "मुफ़्त। बस अपने ईमेल से साइन इन करें।",
    photoAlt: "कई पीढ़ियों का एक मुस्कुराता परिवार, पार्क में साथ खड़ा हुआ",
  },
  // needs native review
  steps: {
    progress: "चरण {current} / {total}",
    basics: "आपके घर के बारे में",
    members: "आपका परिवार",
    documents: "कागज़",
    exclusions: "कुछ और सवाल",
  },
  // needs native review
  basics: {
    title: "आपके घर के बारे में",
    intro: "इससे हम राज्य और आमदनी के नियम जाँच पाते हैं। किसी भी सवाल पर आप “पक्का नहीं पता” चुन सकते हैं।",
    state: "राज्य",
    district: "ज़िला (चाहें तो)",
    area: "आप कहाँ रहते हैं?",
    // needs native review (owner): the house question and its answers
    house: "आपका परिवार किस तरह के घर में रहता है?",
    houseHint: "कच्चा घर मिट्टी, फूस या बाँस का होता है। पक्का घर ईंट या सीमेंट का होता है।",
    income: "पूरे परिवार की सालाना आमदनी",
    incomeHint:
      "साल भर में सब लोग जितना कमाते हैं, उसे जोड़ें: मज़दूरी, खेती, दुकान, पेंशन। मोटा अंदाज़ा भी चलेगा।",
    category: "सामाजिक वर्ग",
    categoryHint: "कुछ योजनाएँ SC, ST या OBC परिवारों के लिए हैं। आप न बताना चाहें तो वह भी चुन सकते हैं।",
    categoryNone: "बताना नहीं चाहते",
    // needs native review (owner): the BPL question, in the owner's chosen words
    bpl: "क्या आपका परिवार गरीबी रेखा से नीचे (BPL) की सूची में है?",
    bplHint: "BPL राशन कार्ड इसका एक संकेत है।",
    saving: "सहेजा जा रहा है…",
  },
  // needs native review
  members: {
    title: "आपका परिवार",
    intro:
      "उन सब लोगों को जोड़ें जो आपके साथ एक घर और एक रसोई में रहते हैं। ज़्यादा से ज़्यादा 20 लोग। पहला नाम या घर का नाम काफ़ी है।",
    add: "एक व्यक्ति जोड़ें",
    addFirst: "पहले अपने आप से शुरू करें।",
    edit: "बदलें",
    remove: "हटाएँ",
    removeConfirm: "{name} को परिवार से हटाएँ?",
    removeYes: "हाँ, हटाएँ",
    removeKeep: "नहीं, रहने दें",
    bornIn: "जन्म वर्ष {year}",
    needOne: "आगे बढ़ने के लिए कम से कम एक व्यक्ति जोड़ें।",
    limitReached: "आप इससे ज़्यादा लोग नहीं जोड़ सकते (20)।",
    formTitleNew: "एक व्यक्ति जोड़ें",
    formTitleEdit: "{name} की जानकारी बदलें",
    nickname: "नाम या घर का नाम",
    nicknameHint: "पहला नाम काफ़ी है। कृपया पूरा कानूनी नाम न लिखें।",
    relation: "यह आपके क्या लगते हैं?",
    birthYear: "जन्म का वर्ष",
    birthYearHint: "जैसे 1985। अंदाज़ा भी चलेगा।",
    birthYearError: "1900 से {max} के बीच का वर्ष लिखें, या खाली छोड़ दें।",
    gender: "लिंग",
    marital: "वैवाहिक स्थिति",
    occupation: "मुख्य काम",
    education: "कितनी पढ़ाई पूरी की",
    student: "क्या यह व्यक्ति अभी पढ़ाई कर रहा है?",
    // needs native review (owner): the study-level question and its answers
    studyLevel: "अभी किस कक्षा में पढ़ रहे हैं?",
    disability: "क्या इस व्यक्ति को कोई विकलांगता है?",
    land: "क्या इस व्यक्ति के नाम खेती की ज़मीन है?",
    remarried: "क्या इस व्यक्ति ने दोबारा शादी की है?",
    saveMember: "इस व्यक्ति को सहेजें",
    saving: "सहेजा जा रहा है…",
    nicknameRequired: "कृपया नाम या घर का नाम लिखें।",
    relationRequired: "कृपया चुनें कि यह आपके क्या लगते हैं।",
  },
  // needs native review
  documents: {
    title: "आपके परिवार के पास कौन-से कागज़ हैं",
    intro:
      "बताइए कि आज आपके पास कौन-से कागज़ हैं। हम कोई नंबर नहीं माँगते, सिर्फ़ यह पूछते हैं कि कागज़ है या नहीं। “पक्का नहीं पता” भी चलेगा।",
    householdTitle: "पूरे परिवार के कागज़",
    householdIntro: "ये पूरे घर के होते हैं, इसलिए एक बार ही जवाब देना है।",
    memberTitle: "{name} के कागज़",
    hasIt: "{name}: क्या यह है?",
    save: "सहेजें और आगे बढ़ें",
    saving: "सहेजा जा रहा है…",
  },
  // needs native review
  exclusions: {
    title: "कुछ और सवाल",
    intro:
      "ये सवाल पीएम-किसान योजना के लिए हैं। कुछ लोगों को यह योजना नहीं मिल सकती, जैसे जिन्होंने आयकर दिया हो। हर वयस्क के लिए जवाब दें। “पक्का नहीं पता” भी चलेगा: तब हम बताएँगे कि नतीजा इसी पर निर्भर है।",
    forName: "{name} के लिए",
    noAdults: "आपकी सूची में कोई वयस्क नहीं है, इसलिए यहाँ कुछ पूछना नहीं है।",
    tax: "क्या इस व्यक्ति ने पिछले साल आयकर दिया?",
    govt: "क्या यह व्यक्ति सरकारी नौकरी करता है या करता था?",
    pension: "क्या इस व्यक्ति को सरकारी पेंशन मिलती है?",
    professional:
      "क्या यह व्यक्ति पंजीकृत डॉक्टर, इंजीनियर, वकील, चार्टर्ड अकाउंटेंट या आर्किटेक्ट है और वही काम करता है?",
    post: "क्या इस व्यक्ति के पास कोई ऊँचा सार्वजनिक पद है या रहा है? जैसे मंत्री, सांसद, विधायक, महापौर या ज़िला पंचायत अध्यक्ष।",
    finish: "सेटअप पूरा करें",
    saving: "सहेजा जा रहा है…",
  },
  // needs native review
  dashboard: {
    // needs native review (owner): the whole-family section
    familyTitle: "पूरे परिवार के लिए",
    familyHint: "ये योजनाएँ किसी एक व्यक्ति पर नहीं, पूरे परिवार पर निर्भर हैं, इसलिए एक ही बार दिखाई गई हैं।",
    title: "आपके परिवार की योजनाएँ",
    checkedOn: "{date} को जाँचा गया",
    summary:
      "आपका परिवार {fit} योजनाओं के लिए पात्र हो सकता है। {close} और योजनाएँ करीब हैं, और {unsure} को एक और जवाब चाहिए।",
    loading: "आपके परिवार के लिए योजनाएँ जाँची जा रही हैं…",
    none: "इस फ़ोन पर आप साइन इन नहीं हैं।",
    toStart: "शुरुआत पर वापस जाएँ",
    toSignIn: "ईमेल से साइन इन करें",
    editHousehold: "घर की जानकारी बदलें",
    // needs native review (owner): the new "add a family member" lines
    addMember: "परिवार का सदस्य जोड़ें",
    addMemberHelp: "हम आपके परिवार के हर व्यक्ति के लिए हर योजना जाँचते हैं।",
    memberAdded: "{name} को जोड़ दिया गया है। उनकी योजनाएँ नीचे हैं।",
    memberUpdated: "{name} की जानकारी बदल दी गई है।",
    memberRemoved: "{name} को हटा दिया गया है।",
    membersFull: "आप इससे ज़्यादा लोग नहीं जोड़ सकते (20)।",
    openingMember: "खुल रहा है…",
    retry: "फिर कोशिश करें",
    skipped: "{count} योजनाएँ जाँची नहीं जा सकीं और छोड़ दी गईं। हम इसे ठीक कर रहे हैं।",
    sections: {
      eligible: "पात्र हो सकते हैं",
      near_miss: "करीब हैं: एक चीज़ कम है",
      unknown: "एक और जवाब चाहिए",
      excluded: "आपके परिवार के लिए उपलब्ध नहीं",
    },
    nothing: "{name} के लिए अभी कोई योजना नहीं मिली।",
    // needs native review (new in PR 3)
    empty: {
      title: "अभी आपके परिवार के लिए कोई योजना नहीं मिली",
      body: "कृपया अपने घर की जानकारी देख लीजिए। राज्य, इलाका और आमदनी से तय होता है कि कौन-सी योजनाएँ मिल सकती हैं। और योजनाएँ जोड़ी जा रही हैं।",
      review: "घर की जानकारी जाँचें",
      allSchemes: "सभी योजनाएँ देखें",
    },
    notFit: "{count} और योजनाएँ उपयुक्त नहीं हैं।",
    excludedBecause: "{names} की वजह से उपलब्ध नहीं।",
    closeHint: "पात्र होने के लिए यह बदलना होगा:",
  },
  // needs native review
  status: {
    eligible: "पात्र हो सकते हैं",
    near_miss: "करीब",
    unknown: "एक और जवाब चाहिए",
    excluded: "उपलब्ध नहीं",
    unverified: "अभी जाँचा नहीं गया",
    verifiedOn: "आख़िरी बार {date} को जाँचा गया",
  },
  // needs native review
  household: {
    title: "घर की जानकारी",
    intro:
      "अपने घर के बारे में कोई भी जवाब बदलें। इससे बदल सकता है कि कौन-सी योजनाएँ ठीक बैठती हैं, इसलिए सहेजने पर हम दोबारा जाँचेंगे।",
    save: "बदलाव सहेजें",
    saving: "सहेजा जा रहा है…",
    loading: "आपके घर की जानकारी लोड हो रही है…",
    cancel: "बिना सहेजे वापस जाएँ",
  },
  // needs native review
  needs: {
    title: "पक्का करने के लिए हमें यह जानना है:",
    answer: "यह बताएँ",
    reasonAge:
      "यह सही उम्र पर निर्भर है। हमारे पास सिर्फ़ जन्म का वर्ष है, इसलिए अभी पक्का नहीं कह सकते।",
    reasonIncome:
      "यह आपके परिवार की सही आमदनी पर निर्भर है। हमारे पास सिर्फ़ वह दायरा है जो आपने चुना, इसलिए अभी पक्का नहीं कह सकते।",
    checkOfficial: "सही सीमा सरकारी वेबसाइट पर मिलेगी।",
    everyone: "आपके परिवार के हर व्यक्ति",
  },
  // needs native review (owner): the questions about the whole family. "anyone" for yes/no facts,
  // "everyone" for the others. See lib/question-text.ts.
  familyQuestions: {
    age: "आपके परिवार के हर व्यक्ति का जन्म किस वर्ष हुआ?",
    gender: "आपके परिवार के हर व्यक्ति पुरुष हैं, महिला हैं या अन्य?",
    marital_status: "आपके परिवार के हर व्यक्ति की वैवाहिक स्थिति क्या है?",
    occupation: "आपके परिवार के हर व्यक्ति का मुख्य काम क्या है?",
    education: "आपके परिवार के हर व्यक्ति ने कितनी पढ़ाई पूरी की?",
    is_student: "क्या आपके परिवार में कोई अभी पढ़ाई कर रहा है?",
    current_study_level: "आपके परिवार का हर विद्यार्थी अभी किस कक्षा में पढ़ रहा है?",
    disability: "क्या आपके परिवार में किसी को कोई विकलांगता है?",
    owns_cultivable_land: "क्या आपके परिवार में किसी के नाम खेती की ज़मीन है?",
    is_remarried: "क्या आपके परिवार में किसी ने दोबारा शादी की है?",
    paid_income_tax_last_year: "क्या आपके परिवार में किसी ने पिछले साल आयकर दिया?",
    govt_employee: "क्या आपके परिवार में कोई सरकारी नौकरी करता है या करता था?",
    pension_band: "क्या आपके परिवार में किसी को सरकारी पेंशन मिलती है?",
    is_registered_professional:
      "क्या आपके परिवार में कोई पंजीकृत डॉक्टर, इंजीनियर, वकील, चार्टर्ड अकाउंटेंट या आर्किटेक्ट है?",
    holds_constitutional_post: "क्या आपके परिवार में किसी के पास कोई ऊँचा सार्वजनिक पद है या रहा है?",
    document: "क्या आपके परिवार में किसी के पास यह कागज़ है: {document}?",
  },
  // needs native review
  questions: {
    age: "{name} का जन्म किस वर्ष हुआ?",
    gender: "{name} पुरुष हैं, महिला हैं या अन्य?",
    marital_status: "{name} की वैवाहिक स्थिति क्या है?",
    occupation: "{name} का मुख्य काम क्या है?",
    education: "{name} ने कितनी पढ़ाई पूरी की?",
    is_student: "क्या {name} अभी पढ़ाई कर रहे हैं?",
    // needs native review (owner): study level
    current_study_level: "{name} अभी किस कक्षा में पढ़ रहे हैं?",
    disability: "क्या {name} को कोई विकलांगता है?",
    owns_cultivable_land: "क्या {name} के नाम खेती की ज़मीन है?",
    is_remarried: "क्या {name} ने दोबारा शादी की है?",
    // needs native review (owner): BPL
    is_bpl: "हमें जानना है कि आपका परिवार गरीबी रेखा से नीचे (BPL) है या नहीं",
    paid_income_tax_last_year: "क्या {name} ने पिछले साल आयकर दिया?",
    govt_employee: "क्या {name} सरकारी नौकरी करते हैं या करते थे?",
    pension_band: "क्या {name} को सरकारी पेंशन मिलती है?",
    is_registered_professional:
      "क्या {name} पंजीकृत डॉक्टर, इंजीनियर, वकील, चार्टर्ड अकाउंटेंट या आर्किटेक्ट हैं?",
    holds_constitutional_post: "क्या {name} के पास कोई ऊँचा सार्वजनिक पद है या रहा है?",
    state: "आपका परिवार किस राज्य में रहता है?",
    district: "आपका परिवार किस ज़िले में रहता है?",
    area_type: "आपका परिवार गाँव में रहता है या कस्बे में?",
    // needs native review (owner): house type
    house_type: "आपका परिवार किस तरह के घर में रहता है?",
    income_band_max: "आपके परिवार की सालाना आमदनी कितनी है?",
    category: "आपके परिवार का सामाजिक वर्ग क्या है?",
    document: "क्या {name} के पास यह कागज़ है: {document}?",
  },
  // needs native review
  scheme: {
    back: "अपने परिवार की योजनाओं पर वापस जाएँ",
    forName: "{name} के लिए",
    // needs native review (owner): whole-family scheme page
    forFamily: "आपके पूरे परिवार के लिए",
    docsFor: "{name} के लिए कागज़:",
    summaryTitle: "आपको क्या मिलता है",
    noSummary: "इस योजना का सरल सार अभी हमारे पास नहीं है। सरकारी वेबसाइट देखें।",
    whyTitle: "यह क्यों ठीक बैठ सकती है",
    met: "जो ठीक बैठता है",
    notMet: "जो ठीक नहीं बैठता",
    // needs native review (owner): renamed from "What we could not check yet"
    notChecked: "आपसे हमें अभी ये जवाब चाहिए",
    fixable: "इसे ठीक किया जा सकता है",
    marks: { met: "पूरा", notMet: "पूरा नहीं", notChecked: "अभी जाँचा नहीं" },
    // needs native review (owner): the "Rules we can't check: ask the office" section
    notCheckedTitle: "जो नियम हम नहीं जाँच सकते: दफ़्तर से पूछें",
    notCheckedIntro: "यह ऐप इन बातों की जाँच नहीं कर सकता। आवेदन से पहले दफ़्तर से पूछें, या सरकारी वेबसाइट पर पढ़ें।",
    excludedTitle: "यह उपलब्ध क्यों नहीं है",
    excludedBecause: "{names} की वजह से:",
    docsTitle: "जो कागज़ अभी चाहिए",
    docsNone: "हमारी जानकारी के अनुसार इस योजना के सारे कागज़ आपके पास हैं।",
    docNo: "आपने बताया कि यह आपके पास नहीं है।",
    docUnknown: "हमें अभी नहीं पता कि यह आपके पास है या नहीं।",
    howToGet: "इसे कैसे बनवाएँ",
    docLink: "इस कागज़ का सरकारी पन्ना",
    officialTitle: "सरकारी स्रोत",
    openOfficial: "सरकारी वेबसाइट खोलें",
    lastChecked: "आख़िरी बार {date} को जाँचा गया",
    unverifiedNote:
      "अभी जाँचा नहीं गया: किसी ने इस योजना के नियमों को सरकारी स्रोत से मिलाकर नहीं देखा है। भरोसा करने से पहले सरकारी वेबसाइट देखें।",
    deadlineEnds: "आवेदन की आख़िरी तारीख़: {date}",
    deadlineStarts: "आवेदन शुरू: {date}",
    notFound: "इस व्यक्ति के लिए यह नतीजा हमें नहीं मिला।",
    chooseMember: "अपने परिवार के पन्ने से कोई योजना खोलें, ताकि हमें पता चले यह किसके लिए है।",
    loading: "लोड हो रहा है…",
  },
  // needs native review
  rules: {
    field: {
      age: "उम्र",
      gender: "लिंग",
      marital_status: "वैवाहिक स्थिति",
      occupation: "मुख्य काम",
      education: "पढ़ाई",
      is_student: "अभी पढ़ाई कर रहे हैं",
      current_study_level: "अभी की कक्षा",
      disability: "विकलांगता है",
      owns_cultivable_land: "खेती की ज़मीन है",
      paid_income_tax_last_year: "पिछले साल आयकर दिया",
      govt_employee: "सरकारी नौकरी",
      pension_band: "सरकारी पेंशन",
      is_registered_professional: "पंजीकृत डॉक्टर, इंजीनियर, वकील, अकाउंटेंट या आर्किटेक्ट",
      holds_constitutional_post: "ऊँचा सार्वजनिक पद है या रहा है",
      is_remarried: "दोबारा शादी की है",
      state: "राज्य",
      district: "ज़िला",
      area_type: "परिवार कहाँ रहता है",
      // needs native review (owner): house type
      house_type: "घर किस तरह का है",
      income_band_max: "परिवार की सालाना आमदनी",
      category: "सामाजिक वर्ग",
      // needs native review (owner): BPL
      is_bpl: "परिवार गरीबी रेखा से नीचे (BPL) की सूची में है",
    },
    hasDocument: "{document} है",
    value: {
      govt: { none: "सरकारी नौकरी नहीं", group_d: "सबसे निचला पद (ग्रुप डी)", other: "कोई और पद" },
      pension: { none: "कोई पेंशन नहीं", below_10k: "महीने में ₹10,000 से कम", "10k_plus": "महीने में ₹10,000 या ज़्यादा" },
    },
    yes: "हाँ",
    no: "नहीं",
    op: {
      eq: "{value}",
      neq: "{value} नहीं",
      in: "{value}",
      not_in: "{value} नहीं",
      gte: "{value} या ज़्यादा",
      lte: "{value} या कम",
      between: "{from} से {to}",
    },
    and: "{first} और {second}",
    anyOf: "इनमें से कम से कम एक: {items}",
    someone: "परिवार में कम से कम एक व्यक्ति: {text}",
    nobody: "परिवार में कोई भी नहीं: {text}",
    not: "यह सही नहीं होना चाहिए: {text}",
    unknownFact: "ऐसी शर्त जो हम अभी शब्दों में नहीं दिखा सकते। सरकारी वेबसाइट देखें।",
  },
  // needs native review
  privacy: {
    title: "आपका डेटा",
    intro:
      "आपके परिवार की जानकारी हमारे सर्वर पर रखी है। हम आपका ईमेल पता सिर्फ़ साइन इन कराने के लिए इस्तेमाल करते हैं। हमारी ईमेल सेवा, Resend, उसे सिर्फ़ आपको कोड भेजने के लिए पाती है। हम इसे बेचते नहीं हैं।",
    signedInAs: "{email} से साइन इन",
    deleteButton: "मेरा डेटा मिटाएँ",
    deleteTitle: "सब कुछ मिटा दें?",
    deleteWarning:
      "इससे आपका परिवार, हर व्यक्ति, सारे जवाब और आपका ईमेल पता हमारे डेटाबेस से हट जाते हैं। इसे वापस नहीं किया जा सकता।",
    deleteYes: "हाँ, मेरा डेटा मिटाएँ",
    deleteNo: "नहीं, डेटा रहने दें",
    deleting: "मिटाया जा रहा है…",
    deletedTitle: "आपका डेटा मिटा दिया गया",
    // needs native review (new in PR 3)
    deletedNote:
      "हमारे काबू से बाहर की प्रतियाँ, जैसे बैकअप या ईमेल सेवा के अपने रिकॉर्ड, कुछ समय तक रह सकती हैं।",
    deletedBody:
      "आपके परिवार की जानकारी और आपका ईमेल पता हमारे डेटाबेस से और इस फ़ोन से मिटा दिए गए हैं।",
    signOutButton: "साइन आउट करें",
    signOutTitle: "इस फ़ोन पर साइन आउट करें?",
    signOutWarning:
      "आपके परिवार की जानकारी हमारे सर्वर पर रहेगी। आप जब चाहें अपने ईमेल से फिर साइन इन कर सकते हैं।",
    signOutYes: "हाँ, साइन आउट करें",
    signOutNo: "नहीं, साइन इन रहने दें",
  },
  // needs native review
  signin: {
    title: "ईमेल से साइन इन करें",
    // needs native review (new in the Google sign-in change): the heading when Google is shown too, "or", the Google lines below.
    titleWithGoogle: "साइन इन करें",
    or: "या",
    intro: "हम आपके ईमेल पर 6 अंकों का कोड भेजते हैं। पासवर्ड की ज़रूरत नहीं है।",
    emailLabel: "आपका ईमेल पता",
    emailHint: "जैसे name@example.com",
    send: "मुझे कोड भेजें",
    sending: "भेजा जा रहा है…",
    privacy:
      "हम आपका ईमेल पता सिर्फ़ साइन इन कराने के लिए इस्तेमाल करते हैं। यह हमारी ईमेल सेवा Resend के पास सिर्फ़ आपको कोड भेजने के लिए जाता है। हम इसे बेचते नहीं हैं।",
    googlePrivacy:
      "अगर आप Google से साइन इन करते हैं, तो Google हमें आपका ईमेल पता बताता है। हम सिर्फ़ ईमेल रखते हैं, आपका नाम या फ़ोटो नहीं।",
    codeTitle: "अपना ईमेल देखें",
    codeIntro: "हमने {email} पर 6 अंकों का कोड भेजा है। यह 10 मिनट तक चलेगा।",
    spam: "नहीं मिला? अपना स्पैम फ़ोल्डर देखें।",
    codeLabel: "6 अंकों का कोड",
    verify: "साइन इन करें",
    verifying: "जाँच हो रही है…",
    resend: "मुझे नया कोड भेजें",
    // needs native review (new in PR 2): the two resend-wait sentences below.
    resendWait: "आप {seconds} सेकंड में नया कोड माँग सकते हैं।",
    resendReady: "अब आप नया कोड माँग सकते हैं।",
    resent: "नया कोड भेजा जा रहा है।",
    otherEmail: "दूसरा ईमेल इस्तेमाल करें",
    invalidEmail: "कृपया अपना पूरा ईमेल पता लिखें, जैसे name@example.com।",
    invalidCodeShape: "कोड में 6 अंक होते हैं। कृपया जाँचें।",
    invalid_code: "यह कोड सही नहीं है। जाँचकर फिर कोशिश करें।",
    attemptsLeft: "{count, plural, one {# कोशिश बाकी है।} other {# कोशिशें बाकी हैं।}}",
    code_expired: "यह कोड पुराना हो गया है। कृपया नया कोड माँगें।",
    too_many_attempts: "बहुत ज़्यादा गलत कोशिशें हुईं। कृपया नया कोड माँगें।",
    too_many_codes: "इस ईमेल के लिए बहुत ज़्यादा कोड माँगे गए। कृपया एक घंटे बाद कोशिश करें।",
    busy: "आज साइन-इन पर भीड़ है। कृपया कल कोशिश करें।",
    email_failed: "हम ईमेल नहीं भेज पाए। कृपया एक मिनट बाद कोशिश करें।",
    invalid_google_token: "हम आपका Google साइन-इन जाँच नहीं पाए। कृपया फिर कोशिश करें, या ईमेल से साइन इन करें।",
    google_unavailable: "Google से साइन-इन अभी उपलब्ध नहीं है। कृपया ईमेल से साइन इन करें।",
  },
  // needs native review
  example: {
    label: "डेमो, असली परिवार नहीं",
    title: "एक डेमो परिवार",
    banner:
      "यह एक काल्पनिक परिवार है, सिर्फ़ यह दिखाने के लिए कि नतीजे कैसे दिखते हैं। इसमें कुछ भी आपके बारे में नहीं है, और यहाँ आप जो भी करें वह सहेजा नहीं जाता।",
    cta: "मेरा अपना परिवार जाँचें",
    back: "उदाहरण पर वापस",
  },
  // needs native review
  options: {
    area: { rural: "गाँव (ग्रामीण)", urban: "कस्बा या शहर (शहरी)" },
    // needs native review (owner): the house answers
    house: {
      no_house: "हमारा अपना कोई घर नहीं है",
      kutcha: "कच्चा घर (मिट्टी, फूस, बाँस)",
      pucca: "पक्का घर (ईंट, सीमेंट)",
    },
    income: {
      up_to_1_lakh: "सालाना ₹1 लाख तक",
      "1_to_2_lakh": "सालाना ₹1 से ₹2 लाख",
      "2_to_2_5_lakh": "सालाना ₹2 से ₹2.5 लाख",
      "2_5_to_3_lakh": "सालाना ₹2.5 से ₹3 लाख",
      "3_to_5_lakh": "सालाना ₹3 से ₹5 लाख",
      "5_to_8_lakh": "सालाना ₹5 से ₹8 लाख",
      above_8_lakh: "सालाना ₹8 लाख से ज़्यादा",
    },
    category: {
      General: "सामान्य",
      SC: "SC (अनुसूचित जाति)",
      ST: "ST (अनुसूचित जनजाति)",
      OBC: "OBC (अन्य पिछड़ा वर्ग)",
    },
    relation: {
      self: "मैं खुद",
      husband: "पति",
      wife: "पत्नी",
      son: "बेटा",
      daughter: "बेटी",
      father: "पिता",
      mother: "माँ",
      grandfather: "दादा / नाना",
      grandmother: "दादी / नानी",
      brother: "भाई",
      sister: "बहन",
      other: "कोई और",
    },
    gender: { male: "पुरुष", female: "महिला", other: "अन्य" },
    marital: {
      unmarried: "अविवाहित",
      married: "विवाहित",
      widow: "विधवा / विधुर",
      divorced: "तलाकशुदा",
      separated: "अलग रह रहे",
    },
    occupation: {
      farmer: "किसान",
      agricultural_labourer: "खेत मज़दूर",
      student: "विद्यार्थी",
      homemaker: "गृहिणी / गृहस्थ",
      self_employed: "अपना काम या दुकान",
      private_job: "निजी नौकरी",
      government_job: "सरकारी नौकरी",
      retired: "रिटायर",
      unemployed: "काम नहीं करते",
      other: "कुछ और",
    },
    education: {
      none: "कभी स्कूल नहीं गए",
      primary: "कक्षा 5 तक",
      secondary: "कक्षा 10 तक",
      senior_secondary: "कक्षा 12 तक",
      graduate: "स्नातक",
      postgraduate: "स्नातकोत्तर",
    },
    // needs native review (owner): the study-level answers
    studyLevel: {
      class_1_8: "कक्षा 1 से 8",
      class_9_10: "कक्षा 9 या 10",
      class_11_12: "कक्षा 11 या 12",
      undergraduate: "कॉलेज (स्नातक)",
      postgraduate: "स्नातकोत्तर",
      other: "कुछ और",
    },
    govt: {
      none: "नहीं",
      group_d: "हाँ, सबसे निचले पद पर (ग्रुप डी या मल्टी-टास्किंग स्टाफ़)",
      other: "हाँ, किसी और पद पर",
    },
    pension: {
      none: "कोई पेंशन नहीं",
      below_10k: "हाँ, महीने में ₹10,000 से कम",
      "10k_plus": "हाँ, महीने में ₹10,000 या उससे ज़्यादा",
    },
  },
  // needs native review (new in PR 3): everything in privacyPage, a first draft. Read it aloud.
  privacyPage: {
    title: "हम आपकी जानकारी कैसे सँभालते हैं",
    intro: "सीधे शब्दों में, कोई छोटे अक्षर नहीं। योजना साथी एक विद्यार्थी का बनाया मुफ़्त प्रोजेक्ट है। यह सरकारी ऐप नहीं है।",
    link: "हम आपकी जानकारी कैसे सँभालते हैं",
    collect: {
      title: "हम क्या रखते हैं",
      intro: "सिर्फ़ वही जो आप हमें बताते हैं:",
      email: "आपका ईमेल पता, आपको साइन इन कराने के लिए।",
      language: "आपकी भाषा: अंग्रेज़ी या हिंदी।",
      home: "आपके घर के बारे में: राज्य, ज़िला (अगर आप लिखें), गाँव या शहर, सालाना आमदनी का दायरा, सामाजिक वर्ग (अगर आप बताना चाहें), और परिवार गरीबी रेखा से नीचे (BPL) की सूची में है या नहीं (हाँ या नहीं, यह भी अगर आप बताना चाहें)।",
      people: "हर व्यक्ति के बारे में: पहला नाम या उपनाम, आपसे रिश्ता, जन्म का साल, और आपके दिए जवाब, जैसे काम, पढ़ाई या खेत की ज़मीन।",
      papers: "हर व्यक्ति के पास कौन-से कागज़ हैं: हाँ, नहीं या पक्का नहीं पता। कागज़ पर लिखा नंबर कभी नहीं।",
      phone: "आपके फ़ोन में: साइन-इन की चाबी, आपकी भाषा, अक्षर का आकार और रंग की पसंद। ये आपके फ़ोन में ही रहते हैं।",
    },
    never: {
      title: "हम क्या कभी नहीं माँगते",
      body: "आधार, पैन, बैंक खाते या कागज़ों के नंबर। फ़ोन नंबर। पासवर्ड।",
    },
    why: {
      title: "हमें इसकी ज़रूरत क्यों है",
      body: "आपको साइन इन कराने के लिए, यह देखने के लिए कि हर व्यक्ति के लिए कौन-सी योजनाएँ ठीक बैठ सकती हैं, और यह दिखाने के लिए कि कौन-से कागज़ कम हैं। इसके अलावा किसी काम के लिए नहीं।",
    },
    how: {
      title: "इसका इस्तेमाल कैसे होता है",
      rules: "तय नियमों से आपके जवाबों को हर योजना से मिलाया जाता है। हर नतीजे में दिखता है कि कौन-से नियम पूरे हुए और कौन-से नहीं।",
      noAi: "आपके जवाब किसी AI सेवा को नहीं भेजे जाते।",
      guidance: "नतीजे सिर्फ़ जानकारी हैं, सरकारी निर्णय नहीं। फ़ैसला सरकारी दफ़्तर करता है।",
    },
    share: {
      title: "और कौन देखता है",
      sell: "हम आपकी जानकारी बेचते नहीं हैं और विज्ञापन के लिए इस्तेमाल नहीं करते।",
      email: "हमारी ईमेल सेवा, Resend, को आपका ईमेल पता और साइन-इन कोड मिलता है, ताकि वह आपको कोड भेज सके।",
      // needs native review (new in the Google sign-in change): the two Google lines.
      google: "अगर आप “Continue with Google” चुनते हैं, तो Google हमें आपका ईमेल पता बताता है। हम सिर्फ़ ईमेल रखते हैं, आपका Google नाम, फ़ोटो या और कुछ नहीं।",
      googleScript: "“Continue with Google” बटन Google की तरफ़ से आता है। जब साइन-इन पेज उसे दिखाता है, तो Google देख सकता है कि पेज खोला गया।",
      hosting: "हमारी होस्टिंग और डेटाबेस सेवाएँ जानकारी हमारे लिए सँभालकर रखती हैं।",
      gov: "हम आपकी तरफ़ से सरकार को कुछ नहीं भेजते।",
    },
    keep: {
      title: "कितने समय तक रखते हैं",
      until: "जब तक आप उसे मिटा न दें।",
      code: "साइन-इन कोड 10 मिनट चलता है। हम उसकी सिर्फ़ उलझी हुई प्रति रखते हैं, कोड खुद नहीं।",
      signedIn: "एक फ़ोन पर साइन इन 30 दिन तक रह सकता है, या जब तक आप साइन आउट न करें।",
    },
    del: {
      title: "कैसे मिटाएँ",
      step1: "साइन इन करके अपना परिवार खोलिए।",
      step2: "पेज के नीचे “मेरा डेटा मिटाएँ” चुनिए।",
      step3: "पक्का कीजिए। इसे वापस नहीं किया जा सकता।",
      removes: "इससे आपका ईमेल पता, आपका परिवार, हर व्यक्ति, सारे जवाब और कागज़ों की जानकारी, और हर नतीजा हमारे डेटाबेस से हट जाता है।",
      limits: "यह हमारे काबू से बाहर की प्रतियों तक नहीं पहुँच सकता। हमारी ईमेल सेवा अपने पास यह रिकॉर्ड रख सकती है कि उसने आपको साइन-इन ईमेल भेजा था, और हमारी होस्टिंग व डेटाबेस सेवाएँ कुछ समय तक बैकअप रख सकती हैं। वे अपने नियमों से चलती हैं।",
      signOut: "“साइन आउट” अलग है: वह सिर्फ़ इस फ़ोन पर साइन-इन खत्म करता है और आपकी जानकारी बनी रहती है।",
    },
    code: {
      title: "खुद देखिए",
      body: "इस ऐप का कोड सबके लिए खुला है।",
    },
  },
  // needs native review (new in PR 3): everything in schemeCard and schemesPage.
  schemeCard: {
    central: "केंद्र सरकार की योजना",
    state: "राज्य की योजना",
    stateNamed: "राज्य की योजना: {state}",
  },
  // needs native review (owner): the myScheme link
  myScheme: {
    link: "myScheme पर और योजनाएँ देखें (Yojana Saathi ने इन्हें जाँचा नहीं है)",
    newTab: "(नए टैब में खुलता है)",
  },
  schemesPage: {
    title: "हम जो सभी योजनाएँ जाँचते हैं",
    intro:
      "आज हम इन योजनाओं को जाँचते हैं। हर योजना के साथ उसकी आधिकारिक वेबसाइट का लिंक है। आपके परिवार को कौन-सी मिल सकती हैं, यह देखने के लिए अपना परिवार जोड़िए।",
    cta: "मेरा परिवार जाँचें",
    loading: "योजनाएँ खुल रही हैं…",
    failed: "अभी योजनाएँ नहीं खुल पाईं। कृपया एक मिनट बाद फिर कोशिश कीजिए।",
    none: "अभी दिखाने के लिए कोई योजना नहीं है।",
  },
  // needs native review: textSize, categories and landing are first drafts, read them aloud.
  textSize: { label: "अक्षर का आकार", normal: "सामान्य अक्षर", large: "बड़े अक्षर" },
  // needs native review: new in PR 2. "Match device" is meant as "same as the phone's own setting".
  theme: { label: "रंग-रूप", light: "हल्का", dark: "गहरा", device: "फ़ोन जैसा" },
  // needs native review: education, health, housing, family_welfare are new
  categories: {
    farmer: "किसान",
    widow_pension: "विधवा पेंशन",
    education: "शिक्षा",
    health: "स्वास्थ्य",
    housing: "आवास",
    family_welfare: "परिवार कल्याण",
    pension: "बुज़ुर्ग",
    other: "अन्य",
  },
  landing: {
    // needs native review: every new line from here to "trust3" (portal redesign)
    categoriesTitle: "विषय के हिसाब से मदद खोजिए",
    categoriesIntro: "कोई विषय चुनिए और देखिए कि आज हमारे पास कौन-सी योजनाएँ हैं। और जोड़ी जा रही हैं।",
    categoriesLabel: "विषय",
    catEducation: "शिक्षा",
    catEducationBody: "विद्यार्थियों और उनके परिवारों के लिए छात्रवृत्ति और मदद।",
    catAgriculture: "खेती",
    catAgricultureBody: "किसान परिवारों के लिए आय सहायता और मदद।",
    catHealthcare: "स्वास्थ्य",
    catHealthcareBody: "परिवार के लिए स्वास्थ्य बीमा और इलाज में मदद।",
    catWomen: "महिला और परिवार",
    catWomenBody: "विधवाओं और महिलाओं के लिए पेंशन और सहायता।",
    catSeniors: "वरिष्ठ नागरिक",
    catSeniorsBody: "बुज़ुर्गों के लिए पेंशन और सहायता।",
    catFamilies: "परिवार",
    catFamiliesBody: "पूरे घर को एक साथ देखने वाली मदद।",
    countOne: "{count} योजना",
    countMany: "{count} योजनाएँ",
    comingSoon: "जल्द आ रहा है",
    countChecking: "देख रहे हैं…",
    countsFailed: "अभी योजनाओं की संख्या नहीं खुल पाई। आप फिर भी सभी योजनाएँ देख सकते हैं।",
    trustTitle: "हम इसे ईमानदार कैसे रखते हैं",
    trust1: "हर योजना अपने आधिकारिक स्रोत से जुड़ी है",
    // needs native review (reworded in PR 2: "whether and when")
    trust2: "हर योजना बताती है कि उसे जाँचा गया है या नहीं, और आख़िरी बार कब",
    trust3: "हम आधार नंबर कभी नहीं माँगते। अपना डेटा जब चाहें मिटाइए।",
    howTitle: "यह कैसे काम करता है",
    step1Title: "अपने परिवार के बारे में बताइए",
    step1Body: "हर सदस्य को एक बार जोड़िए: उम्र, काम और कुछ आसान बातें। इसमें लगभग पाँच मिनट लगते हैं।",
    step2Title: "देखिए हर सदस्य को क्या मिल सकता है",
    step2Body: "हम हर सदस्य को सरकारी योजनाओं से मिलाकर वे योजनाएँ दिखाते हैं जो उसके लिए ठीक हो सकती हैं।",
    step3Title: "जानिए कौन-से कागज़ बनवाने हैं",
    step3Body: "हम बताते हैं कि कौन-से कागज़ कम हैं और उन्हें कैसे बनवाएँ। जिन योजनाओं के आप करीब हैं, वे भी दिखाते हैं।",
    // needs native review (new in PR 3)
    seeAllSchemes: "सभी योजनाएँ देखें",
    officialSite: "आधिकारिक वेबसाइट",
    privacyLink: "हम आपकी जानकारी कैसे सँभालते हैं",
    emailPromise: "हम आपका ईमेल पता सिर्फ़ साइन इन कराने के लिए इस्तेमाल करते हैं। यह हमारी ईमेल सेवा Resend के पास सिर्फ़ आपको कोड भेजने के लिए जाता है। हम इसे बेचते नहीं हैं।",
    faqTitle: "लोग अक्सर पूछते हैं",
    faq1Q: "क्या इसमें पैसे लगते हैं?",
    faq1A: "नहीं। यह मुफ़्त है। आपको बस अपने ईमेल से साइन इन करना होता है।",
    faq2Q: "क्या मुझे अपना आधार नंबर देना होगा?",
    faq2A: "नहीं। हम बस पूछते हैं कि आपके पास कागज़ है या नहीं, हाँ या ना। नंबर कभी नहीं पूछते।",
    faq3Q: "क्या यह सरकारी ऐप है?",
    faq3A: "नहीं। यह एक विद्यार्थी का बनाया मुफ़्त प्रोजेक्ट है। इसका किसी सरकारी दफ़्तर से कोई संबंध नहीं है।",
    faq4Q: "क्या “पात्र हो सकते हैं” पक्का वादा है?",
    faq4A: "नहीं। यह केवल जानकारी है। फ़ैसला सरकारी दफ़्तर करता है। आवेदन से पहले आधिकारिक वेबसाइट ज़रूर देखिए।",
    faq5Q: "मैं अपनी जानकारी कैसे मिटाऊँ?",
    faq5A: "अपना परिवार खोलिए। पेज के नीचे “मेरा डेटा मिटाएँ” चुनिए। आपके परिवार की सारी जानकारी और आपका ईमेल पता मिट जाएगा।",
    aboutTitle: "इस प्रोजेक्ट के बारे में",
    aboutBody: "योजना साथी एक विद्यार्थी का बनाया मुफ़्त प्रोजेक्ट है। यह सरकारी ऐप नहीं है। यह केवल जानकारी देता है, सरकारी निर्णय नहीं।",
    github: "कोड GitHub पर देखिए",
  },
};
