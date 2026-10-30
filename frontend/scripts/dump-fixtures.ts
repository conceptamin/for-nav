// 백엔드 규칙 동기화 테스트(backend/tests/test_parity.py)의 기대값을 프론트 도메인 함수로 만든다.
// 사람이 기대값을 적지 않는다. 입력 목록만 여기에 두고 출력은 프론트 코드가 낸다.
//
//   cd frontend
//   npx rolldown scripts/dump-fixtures.ts --file /tmp/dump.mjs --format esm \
//     && TZ=Asia/Seoul node /tmp/dump.mjs > ../backend/tests/fixtures/parity.json
//
// 운영 시간·mock 시각은 로컬 시각을 쓰므로 반드시 TZ=Asia/Seoul로 실행한다.

import { buildMockCases, buildStatRecords, rng } from '../src/data/mock';
import { rateUrgency } from '../src/domain/centerCase';
import type { CoverageInput } from '../src/domain/coverage';
import { isAfterHours, nextOpenDay, routeCoverage } from '../src/domain/coverage';
import type { ContactMethod, Profile, ReportField, RequestType } from '../src/domain/templates';
import { buildCallScript, buildCenterSummary, buildClinicianReport, buildDeskSheet, REPORT_FIELDS } from '../src/domain/templates';
import type { Intake } from '../src/domain/triage';
import { extractFromText, mergeExtraction, recommendDepartment, triage } from '../src/domain/triage';
import type { BodyPart, Lang, Symptom, YesNoUnknown } from '../src/domain/vocab';
import { BODY_PARTS, LANGS, SYMPTOMS } from '../src/domain/vocab';

if (new Date('2026-10-26T00:00:00Z').getHours() !== 9) {
  throw new Error('TZ=Asia/Seoul로 실행해야 한다');
}

const NOW = new Date('2026-10-26T01:00:00.000Z');

const intake = (over: Partial<Intake>): Intake => ({
  id: 'in-test',
  language: 'en',
  bodyParts: [],
  symptoms: [],
  freeText: '',
  onset: null,
  workRelated: null,
  workType: null,
  industry: null,
  district: null,
  createdAt: NOW.toISOString(),
  ...over,
});

// ---------------------------------------------------------------------------
// 응급 판정·진료과
// ---------------------------------------------------------------------------
// 응급 키워드 종류마다 언어별 1개씩. en·vi·ko를 뺀 언어의 예문은 기계 번역 초안이다(backlog 16)
const EMERGENCY_TEXTS: Record<Lang, string[]> = {
  ko: [
    '동료가 쓰러져서 의식이 없어요',
    '숨을 못 쉬겠어요',
    '가슴이 아프고 식은땀이 나요',
    '피가 멈추지 않아요',
    '손가락이 잘렸어요',
    '비계에서 추락했어요',
    '갑자기 경련을 해요',
    '한쪽 팔다리에 마비가 왔어요',
    '작업 중 감전됐어요',
    '눈에 화학물질이 튀었어요',
    '가스를 마시고 어지러워요',
  ],
  en: [
    'My coworker fainted',
    "I can't breathe",
    'I have chest pain',
    "It won't stop bleeding",
    'My finger was cut off',
    'He fell from the scaffold',
    'He is having a seizure',
    'My speech is slurred',
    'I got an electric shock',
    'Chemical in my eye',
    'I inhaled gas at work',
  ],
  vi: [
    'Anh ấy bị ngất',
    'Tôi khó thở quá',
    'Tôi bị đau ngực',
    'Máu chảy không ngừng',
    'Bị đứt lìa ngón tay',
    'Anh ấy ngã từ trên cao',
    'Anh ấy bị co giật',
    'Tôi bị méo miệng',
    'Tôi bị điện giật',
    'Hóa chất bắn vào mắt',
    'Tôi bị ngộ độc khí',
  ],
  ne: [
    "मेरो साथी काममा अचानक बेहोस भयो।",
    "मलाई सास फेर्न सकिँदैन, धेरै डर लाग्यो।",
    "बिहानदेखि छाती दुखिरहेको छ।",
    "हात काटियो, धेरै रगत बगिरहेको छ।",
    "मेसिनमा मेरो औंला छिनियो।",
    "मेरो साथी मचानमाथिबाट खस्यो।",
    "साथीलाई मिर्गी आएजस्तो भयो, शरीर तन्किरहेको छ।",
    "अचानक मुख बाङ्गो भयो र हात चल्दैन।",
    "वेल्डिङ गर्दा करेन्ट लाग्यो।",
    "आँखामा केमिकल पर्‍यो, आँखा खोल्न सकिनँ।",
    "कारखानामा ग्यास चुहियो, टाउको दुख्यो।",
  ],
  ru: [
    "Мой друг упал и потерял сознание, не отвечает",
    "Коллега не может дышать после работы в цеху",
    "У меня сильная боль в груди, отдает в руку",
    "Порезал руку, кровь не останавливается",
    "Станком отрезало палец на правой руке",
    "Рабочий упал с высоты на стройке",
    "У человека припадок, он трясется на полу",
    "Отец не может говорить, лицо перекосило",
    "Сварщика ударило током на заводе",
    "Химия попала в глаз, сильно жжет",
    "На заводе утечка газа, людям плохо",
  ],
  mn: [
    "Найз маань ухаан алдаад унасан.",
    "Би амьсгалж чадахгүй байна, туслаарай!",
    "Цээж өвдөөд байна, зүүн гар луу дамжиж байна.",
    "Гар зүсэгдээд цус зогсохгүй байна.",
    "Машинд хуруу тасарсан.",
    "Хамт ажилладаг хүн өндрөөс унасан.",
    "Ажилчин гэнэт таталт өгөөд унасан.",
    "Аавын биеийн нэг тал нь хөдлөхгүй байна.",
    "Ажил дээр цахилгаанд цохиулсан.",
    "Нүдэнд химийн бодис орсон.",
    "Үйлдвэрт хий алдагдаад толгой эргэж байна.",
  ],
  my: [
    "သူငယ်ချင်း အလုပ်မှာ ရုတ်တရက် သတိလစ်သွားတယ်။",
    "အသက်ရှူမရဘူး၊ အရမ်းကြောက်တယ်။",
    "မနက်ကတည်းက ရင်ဘတ်နာနေတယ်။",
    "လက်ပြတ်ရှပြီး သွေးမတိတ်ဘူး။",
    "စက်ထဲညပ်ပြီး လက်ချောင်းပြတ်ထွက်သွားတယ်။",
    "သူငယ်ချင်း ငြမ်းပေါ်က အမြင့်ကပြုတ်ကျတယ်။",
    "သူငယ်ချင်း ဝက်ရူးပြန်သလို တက်နေတယ်။",
    "ရုတ်တရက် ပါးစပ်ရွဲ့သွားပြီး လက်မလှုပ်နိုင်ဘူး။",
    "ဂဟေဆော်နေတုန်း ဓာတ်လိုက်သွားတယ်။",
    "မျက်လုံးထဲဓာတုဆေး ဝင်သွားတယ်၊ မျက်လုံးမဖွင့်နိုင်ဘူး။",
    "စက်ရုံမှာ ဓာတ်ငွေ့ယိုပြီး ခေါင်းကိုက်တယ်။",
  ],
  si: [
    "මගේ යාළුවා වැඩ කරද්දී සිහිය නැති වුණා.",
    "මට හුස්ම ගන්න බැහැ, හරිම බයයි.",
    "උදේ ඉඳන් පපුවේ වේදනාවක් තියෙනවා.",
    "අත කැපුණා, ලේ නවතින්නේ නැහැ.",
    "මැෂිමට අහු වෙලා ඇඟිල්ල කැපිලා වෙන් වුණා.",
    "යාළුවා පලංචියේ උඩින් වැටුණා.",
    "යාළුවාට වලිප්පුවක් ආවා.",
    "හදිසියේම කට ඇද වුණා, අත හොලවන්න බැහැ.",
    "වෙල්ඩින් කරද්දී කරන්ට් වැදුණා.",
    "ඇසට රසායනයක් ගියා, ඇස අරින්න බැහැ.",
    "ෆැක්ටරියේ ගෑස් කාන්දු වුණා, ඔළුව රිදෙනවා.",
  ],
  ar: [
    "زميلي سقط على الأرض وفقد الوعي",
    "لا أستطيع التنفس جيدا",
    "عندي ألم في الصدر منذ ساعة",
    "يدي فيها نزيف شديد",
    "الآلة قطعت إصبعي والإصبع مبتور",
    "زميلي سقط من فوق السقالة",
    "صديقي عنده تشنجات ولا يتكلم",
    "زميلي لا يحرك نصف الجسم الأيمن",
    "تعرض زميلي لصعق كهربائي في المصنع",
    "دخلت مادة كيميائية في عيني",
    "يوجد تسرب غاز في المصنع ورأسي يؤلمني",
  ],
  uz: [
    "Hamkasbim hushidan ketib yiqildi.",
    "Nafas ololmayapman, yordam bering!",
    "Koʻkragim ogʻriyapti, chap qoʻlimgacha boryapti.",
    "Qoʻlim kesildi, qon tinmay oqyapti.",
    "Stanokda barmogʻim kesilib tushdi.",
    "Ishchi balanddan yiqilib tushdi.",
    "Doʻstimni tutqanoq tutyapti.",
    "Otamning tanasining bir tomoni ishlamayapti.",
    "Ishda meni tok urdi.",
    "Koʻzimga kimyoviy modda sachradi.",
    "Zavodda gaz sizib chiqdi, boshim aylanyapti.",
  ],
  ja: [
    "同僚が倒れて意識がないです。",
    "急に息ができない、助けてください。",
    "さっきから胸が痛くて冷や汗が出ます。",
    "手を切って血が止まらないです。",
    "プレスで指がちぎれました。",
    "足場から落ちて腰を強く打ちました。",
    "同僚が急にけいれんを起こしています。",
    "右の手足が麻痺して動きません。",
    "作業中に感電して手が黒くなりました。",
    "目に薬品が入って開けられません。",
    "タンクの中でガスを吸って頭がふらふらします。",
  ],
  'zh-CN': [
    "我的同事突然晕倒了，叫不醒。",
    "我喘不过气，快要不行了。",
    "从刚才开始胸口痛，还出冷汗。",
    "手被割伤了，一直流血不止。",
    "我的手指被机器切断了。",
    "同事从脚手架上摔下来了。",
    "他突然倒在地上抽搐。",
    "我的半边身体动不了，说话也口齿不清。",
    "工作的时候触电了，手烧黑了。",
    "化学品溅到眼睛里了，睁不开。",
    "在罐子里面吸入毒气，头很晕。",
  ],
  'zh-TW': [
    "我同事突然昏倒了，叫不醒。",
    "我喘不過氣，快不行了。",
    "從剛才開始胸口很痛，還一直冒冷汗。",
    "手被割到，一直流血停不下來。",
    "我的手指被機器切斷了。",
    "同事從鷹架上摔下來了。",
    "他突然倒在地上抽搐。",
    "我的半邊身體不能動，講話也口齒不清。",
    "工作的時候觸電了，手燒黑了。",
    "化學品濺到眼睛裡了，張不開。",
    "工廠瓦斯外洩，大家都頭暈。",
  ],
  kk: [
    "Досым құлап, есінен танып қалды",
    "Әріптесім дем ала алмай жатыр",
    "Кеудем ауырып тұр, қолыма береді",
    "Қолымды кесіп алдым, қан тоқтамай жатыр",
    "Станокта саусағым кесіліп түсті",
    "Жұмысшы құрылыста биіктен құлап кетті",
    "Адамның талмасы ұстап, жерде жатыр",
    "Әкемнің беті қисайып, сөйлей алмай жатыр",
    "Дәнекерлеушіні зауытта ток соқты",
    "Жұмыста көзіме химия тиіп кетті",
    "Зауытта газ шығып жатыр, адамдар уланды",
  ],
  km: [
    "មិត្តរួមការងារខ្ញុំដួលសន្លប់",
    "ខ្ញុំដកដង្ហើមមិនរួចទេ",
    "ខ្ញុំឈឺទ្រូងខ្លាំងណាស់",
    "ដៃខ្ញុំហូរឈាមច្រើនមិនឈប់",
    "ម៉ាស៊ីនកាត់ដាច់ម្រាមដៃខ្ញុំ",
    "មិត្តខ្ញុំធ្លាក់ពីរន្ទានៅកន្លែងសាងសង់",
    "មិត្តខ្ញុំប្រកាច់ ហើយមិនឆ្លើយ",
    "មិត្តខ្ញុំមាត់វៀច ហើយនិយាយលែងច្បាស់",
    "ខ្ញុំត្រូវឆក់ភ្លើងពេលជួសជុលម៉ាស៊ីន",
    "សារធាតុគីមីខ្ទាតចូលភ្នែកខ្ញុំ",
    "មានហ្គាសលេចនៅរោងចក្រ ខ្ញុំវិលមុខ",
  ],
  ky: [
    "Досум жыгылып, эсин жоготуп койду",
    "Кесиптешим дем ала албай жатат",
    "Көкүрөгүм ооруп жатат, колума берип жатат",
    "Колумду кесип алдым, кан токтобой жатат",
    "Станокто манжам кесилип түштү",
    "Жумушчу курулушта бийиктиктен кулап кетти",
    "Адамды талма кармап, жерде жатат",
    "Атамдын бети кыйшайып, сүйлөй албай жатат",
    "Ширетүүчүнү заводдо ток урду",
    "Жумушта көзүмө химия тийип кетти",
    "Заводдо газ чыгып жатат, адамдар ууланды",
  ],
  th: [
    "เพื่อนร่วมงานล้มลงแล้วหมดสติ",
    "หายใจไม่ออกเลย ช่วยด้วย",
    "เจ็บหน้าอกมากตั้งแต่เมื่อเช้า",
    "มือโดนบาดแล้วเลือดไหลไม่หยุด",
    "นิ้วขาดเพราะเครื่องปั๊ม",
    "เพื่อนตกจากนั่งร้านที่อู่ต่อเรือ",
    "เพื่อนมีอาการชักเกร็งและไม่ตอบ",
    "เพื่อนปากเบี้ยวและพูดไม่ชัด",
    "โดนไฟดูดตอนซ่อมเครื่อง",
    "สารเคมีเข้าตาตอนทำงาน",
    "มีแก๊สรั่วในโรงงาน ปวดหัวมาก",
  ],
  fr: [
    "Mon collègue s'est évanoui à l'usine et ne répond plus.",
    "Je ne peux pas respirer après la fumée de soudure.",
    "J'ai très mal à la poitrine depuis ce matin.",
    "Ma main saigne beaucoup, ça ne s'arrête pas.",
    "Mon doigt a été sectionné par la presse.",
    "Il est tombé de l'échafaudage, environ trois mètres.",
    "Mon ami a des convulsions sur le sol.",
    "Mon bras et ma jambe sont paralysés d'un seul coup.",
    "Un collègue a été électrocuté sur le chantier.",
    "J'ai reçu un produit chimique dans les yeux au travail.",
    "Il y a une fuite de gaz et j'ai mal à la tête.",
  ],
  tl: [
    "Nahimatay ang katrabaho ko sa pabrika at hindi siya sumasagot.",
    "Hindi makahinga ang kasama ko pagkatapos ng usok sa welding.",
    "Sobrang sakit sa dibdib ko mula kaninang umaga.",
    "Maraming dugo sa kamay ko at hindi tumitigil.",
    "Naputulan ako ng daliri sa press machine.",
    "Nahulog mula sa scaffolding ang kasama ko, mga tatlong metro.",
    "Nangingisay ang kaibigan ko sa sahig.",
    "Biglang naparalisa ang kaliwang braso at binti niya.",
    "Nakuryente ang katrabaho ko sa site.",
    "Tumalsik ang kemikal sa mata ko habang nagtatrabaho.",
    "May tagas ng gas sa pabrika at nahihilo ako.",
  ],
  id: [
    "Teman kerja saya pingsan di pabrik dan tidak menjawab.",
    "Saya tidak bisa bernapas setelah menghirup asap las.",
    "Saya merasa nyeri dada sejak tadi pagi.",
    "Tangan saya banyak darah dan tidak mau berhenti.",
    "Tolong, jari putus kena mesin press!",
    "Teman saya jatuh dari perancah sekitar tiga meter.",
    "Teman saya kejang-kejang di lantai.",
    "Lengan dan kaki kirinya tiba-tiba lumpuh.",
    "Teman kerja saya tersengat listrik di proyek.",
    "Cairan kimia masuk ke mata saya waktu kerja.",
    "Ada kebocoran gas di pabrik dan saya pusing.",
  ],
};

const triageInputs: Intake[] = [];
for (const lang of LANGS) {
  for (const freeText of EMERGENCY_TEXTS[lang]) {
    triageInputs.push(intake({ language: lang, bodyParts: ['whole'], symptoms: ['pain'], freeText }));
  }
}
// 머리 부상: 구토·어지러움이 있을 때만 응급
triageInputs.push(
  intake({ language: 'ko', bodyParts: ['head'], symptoms: ['pain'], freeText: '머리를 부딪쳤는데 토했어요' }),
  intake({ language: 'en', bodyParts: ['head'], symptoms: ['dizzy'], freeText: 'I hit my head on a beam' }),
  intake({ language: 'vi', bodyParts: ['head'], symptoms: ['nausea'], freeText: 'Tôi bị đập đầu' }),
  intake({ language: 'ko', bodyParts: ['head'], symptoms: ['pain'], freeText: '머리를 부딪쳤어요' }),
  intake({ language: 'en', bodyParts: ['head'], symptoms: ['pain'], freeText: 'head injury, no other problem' }),
);
// 보조 점수 경계값(2점 → 비응급, 3점 → 응급)
triageInputs.push(
  intake({ language: 'vi', bodyParts: ['hand'], symptoms: ['cut', 'bleeding'] }),
  intake({ language: 'vi', bodyParts: ['hand'], symptoms: ['cut', 'bleeding'], freeText: 'Rất đau' }),
  intake({ language: 'en', bodyParts: ['head'], symptoms: ['burn'] }),
  intake({ language: 'en', bodyParts: ['head'], symptoms: ['burn'], freeText: 'it is terrible' }),
  intake({ language: 'ko', bodyParts: ['head'], symptoms: ['dizzy', 'nausea'] }),
  intake({ language: 'ko', bodyParts: ['back'], symptoms: ['cantmove', 'chemical'] }),
  intake({ language: 'ko', bodyParts: ['back'], symptoms: ['cantmove', 'chemical'], freeText: '너무 아파요' }),
  intake({ language: 'en', bodyParts: ['whole'], symptoms: ['fever', 'dizzy', 'nausea'] }),
  intake({ language: 'en', bodyParts: ['whole'], symptoms: ['bleeding', 'burn'] }),
);
// 버튼 조합 규칙과 진료과 규칙표: 부위 × 증상 한 쌍씩 전부
for (const b of Object.keys(BODY_PARTS) as BodyPart[]) {
  for (const s of Object.keys(SYMPTOMS) as Symptom[]) {
    triageInputs.push(intake({ bodyParts: [b], symptoms: [s] }));
  }
}
// 여러 부위·증상 조합과 빈 입력
triageInputs.push(
  intake({ bodyParts: ['skin', 'hand'], symptoms: ['chemical', 'rash'] }),
  intake({ bodyParts: ['eye', 'hand'], symptoms: ['cut'] }),
  intake({ bodyParts: ['teeth', 'head'], symptoms: ['burn'] }),
  intake({ bodyParts: ['head', 'arm'], symptoms: ['numb'] }),
  intake({ bodyParts: ['head', 'abdomen'], symptoms: ['pain'] }),
  intake({ bodyParts: ['chest', 'back'], symptoms: ['pain'] }),
  intake({ bodyParts: [], symptoms: [] }),
  intake({ bodyParts: ['hand'], symptoms: [] }),
  intake({ bodyParts: [], symptoms: ['pain'], freeText: 'I fell from a ladder' }),
  intake({ language: 'en', bodyParts: ['arm'], symptoms: ['rash'], freeText: 'Rash after painting the ship' }),
);

// ---------------------------------------------------------------------------
// 자유 입력 추출
// ---------------------------------------------------------------------------
const EXTRACT_TEXTS = [
  'Ngón tay bị kẹp vào máy dập, bị sưng.',
  'Tôi bị đau lưng ở nhà máy hôm qua.',
  'Tôi bị đau lưng ở nhà sau giờ làm.',
  'Bụi vào mắt khi đang mài.',
  'Bị bỏng nhẹ ở tay khi hàn điện.',
  'Sốt và ho 3 ngày.',
  'Ngứa, mẩn đỏ ở tay, có thể do sơn.',
  'Đau răng một tuần.',
  'Đau bụng và nôn từ hôm qua.',
  'Da bị rát sau khi tiếp xúc hóa chất',
  'My finger got caught in the press machine, it is swollen.',
  'Back pain after lifting heavy parts.',
  'Rash after painting the ship',
  'I hurt my knee at work this morning',
  'I have a cough, fever and my throat is sore for a few days',
  'Something in my eye while grinding',
  'I cut my hand at home last night and it bleeds',
  'My ear hurts',
  'Stomach ache for a week',
  'pain',
  '프레스 기계에 손가락이 끼어서 부었어요',
  '무거운 걸 들다가 허리를 다쳤어요. 어제부터 아파요',
  '용접하다가 팔에 화상을 입었어요',
  '집에서 넘어져서 무릎이 아파요',
  '며칠째 기침하고 열이 나요',
  '눈에 뭐가 들어갔어요',
  '공장에서 시너 냄새를 맡고 어지러워요',
  '온몸이 가렵고 두드러기가 났어요',
  '',
];
const extractCases = EXTRACT_TEXTS.flatMap((freeText, n) => {
  const empty = intake({ language: (['vi', 'en', 'ko'] as Lang[])[n % 3]!, freeText });
  const preset = intake({ language: 'en', freeText, bodyParts: ['leg'], onset: 'week', workRelated: 'no' });
  return [empty, preset].map((i) => {
    const extraction = extractFromText(i.freeText);
    return { input: i, output: { extraction, intake: mergeExtraction(i, extraction) } };
  });
});

// ---------------------------------------------------------------------------
// 제도 경로·긴급도
// ---------------------------------------------------------------------------
const YNU: YesNoUnknown[] = ['yes', 'no', 'unknown'];
const routeCases: { input: CoverageInput; output: unknown }[] = [];
for (const workRelated of YNU) {
  for (const insurance of YNU) {
    for (const ulsan90 of [...YNU, null]) {
      const input = { workRelated, insurance, ulsan90 };
      routeCases.push({ input, output: routeCoverage(input) });
    }
  }
}

const urgencyCases = [true, false].flatMap((emergencyFlag) =>
  [...YNU, null].flatMap((workRelated) =>
    [...YNU, null].map((insurance) => {
      const input = { emergencyFlag, workRelated, insurance };
      return { input, output: rateUrgency(input) };
    }),
  ),
);

// ---------------------------------------------------------------------------
// 템플릿: 언어 20종 × 첫 방문 여부 × 업무 관련 여부
// ---------------------------------------------------------------------------
const TEMPLATE_INTAKES: Partial<Intake>[] = [
  { bodyParts: ['hand'], symptoms: ['cut', 'bleeding'], onset: 'today', workType: 'grinding', industry: 'shipbuilding', district: 'dong', freeText: 'Cut on a steel plate' },
  { bodyParts: ['head', 'eye'], symptoms: ['pain'], onset: null },
  { bodyParts: ['back'], symptoms: ['swelling'], onset: 'days', workType: 'lifting', industry: 'autoparts' },
  { bodyParts: ['abdomen'], symptoms: ['nausea', 'dizzy'], onset: 'week', district: 'ulju', freeText: '어제부터 토했어요' },
  { bodyParts: [], symptoms: [] },
];
const WORK: (YesNoUnknown | null)[] = ['yes', 'no', 'unknown', null];

const deskCases: unknown[] = [];
const callCases: unknown[] = [];
for (const lang of LANGS) {
  TEMPLATE_INTAKES.forEach((over, n) => {
    for (const workRelated of WORK) {
      const i = intake({ ...over, language: lang, workRelated });
      const department = i.bodyParts.length && i.symptoms.length ? recommendDepartment(i.bodyParts, i.symptoms).primary : 'family';
      for (const firstVisit of [true, false]) {
        deskCases.push({ input: { intake: i, department, firstVisit, lang }, output: buildDeskSheet(i, department, firstVisit, lang) });
      }
      if (workRelated === WORK[n % WORK.length]) {
        callCases.push({ input: { intake: i, department, lang }, output: buildCallScript(i, department, lang) });
      }
    }
  });
}

const PROFILES: (Profile | null)[] = [
  null,
  { birthDate: '1995-03-10', sex: 'male', height: 170, weight: 65.5, drinking: 'sometimes', smoking: 'quit' },
  { birthDate: '2000-12-31', sex: 'female', height: null, weight: null, drinking: null, smoking: 'no' },
  { birthDate: 'not-a-date', sex: 'female', height: 158.2, weight: 0, drinking: 'often', smoking: null },
];
const INCLUDED: ReportField[][] = [[...REPORT_FIELDS], ['symptoms', 'bodyParts', 'note'], []];
const clinicianCases: unknown[] = [];
for (const lang of LANGS) {
  TEMPLATE_INTAKES.forEach((over, n) => {
    const i = intake({ ...over, language: lang, workRelated: WORK[n % WORK.length]! });
    INCLUDED.forEach((included, k) => {
      const profile = PROFILES[(n + k) % PROFILES.length]!;
      const meds = k === 0 ? 'Paracetamol 500mg' : '';
      const { id: _id, createdAt: _createdAt, ...output } = buildClinicianReport(i, included, profile, meds);
      clinicianCases.push({ input: { intake: i, included, profile, meds }, output });
    });
  });
}

const REQUESTS: RequestType[] = ['booking', 'interpret', 'policy', 'referral', 'other'];
const CONTACTS: (ContactMethod | null)[] = ['phone', 'sms', 'kakao', 'zalo', 'visit', null];
const INSURANCE: (YesNoUnknown | null)[] = ['yes', 'no', 'unknown', null];
const centerCases: unknown[] = [];
let k = 0;
for (const lang of LANGS) {
  for (const over of TEMPLATE_INTAKES) {
    for (const workRelated of WORK) {
      const i = intake({ ...over, language: lang, workRelated });
      const insurance = INSURANCE[k % INSURANCE.length]!;
      const coverage = k % 3 === 0 ? null : routeCoverage({ workRelated: workRelated ?? 'unknown', insurance: insurance ?? 'unknown', ulsan90: k % 2 ? 'yes' : 'no' });
      const input = {
        intake: i,
        emergencyFlag: k % 5 === 0,
        requestType: REQUESTS[k % REQUESTS.length]!,
        coverage,
        insurance,
        contactMethod: CONTACTS[k % CONTACTS.length]!,
      };
      centerCases.push({ input, output: buildCenterSummary(input) });
      k += 1;
    }
  }
}

// ---------------------------------------------------------------------------
// 운영 시간(Asia/Seoul)
// ---------------------------------------------------------------------------
const ymd = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
const hoursCases: unknown[] = [];
// 2026-10-23(금) 00:00 KST부터 5일 동안 1시간 간격 + 경계 직전·직후
for (let h = 0; h < 24 * 5; h += 1) {
  const base = new Date(Date.UTC(2026, 9, 22, 15) + h * 3600000);
  for (const at of [base, new Date(base.getTime() - 1)]) {
    hoursCases.push({ input: at.toISOString(), output: { afterHours: isAfterHours(at), nextOpenDate: ymd(nextOpenDay(at)) } });
  }
}

// ---------------------------------------------------------------------------
// mock 데이터
// ---------------------------------------------------------------------------
const firstTen = (seed: number) => {
  const r = rng(seed);
  return Array.from({ length: 10 }, () => r());
};

const out = {
  generatedAt: new Date().toISOString(),
  now: NOW.toISOString(),
  triage: triageInputs.map((input) => ({ input, output: triage(input) })),
  extract: extractCases,
  route: routeCases,
  urgency: urgencyCases,
  desk: deskCases,
  call: callCases,
  clinician: clinicianCases,
  center: centerCases,
  hours: hoursCases,
  rng: { 20261024: firstTen(20261024), 77: firstTen(77) },
  mockCases: buildMockCases(NOW),
  statRecords: buildStatRecords(NOW).map((r) => ({ ...r, date: r.date.toISOString() })),
};

console.log(JSON.stringify(out, null, 1));
