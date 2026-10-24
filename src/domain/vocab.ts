// 고정 어휘: 신체 부위·증상·진료과·업종·구군 등.
// 모든 항목은 한국어(의료진·센터 표시), 영어·베트남어(근로자 표시), 발음 표기(전화 스크립트용)를 함께 가진다.

export type Lang = 'en' | 'vi';
export const LANGS: Lang[] = ['en', 'vi'];

export interface Term {
  ko: string;
  en: string;
  vi: string;
  /** 영어 사용자용 로마자 발음 */
  roman: string;
  /** 베트남어 사용자용 발음 표기 */
  viPron: string;
}

/** 근로자 언어에 맞는 발음 표기 */
export function pron(term: Term, lang: Lang): string {
  return lang === 'vi' ? term.viPron : term.roman;
}

export const BODY_PARTS = {
  head: { ko: '머리', en: 'Head', vi: 'Đầu', roman: 'meo-ri', viPron: 'mơ-ri' },
  eye: { ko: '눈', en: 'Eye', vi: 'Mắt', roman: 'nun', viPron: 'nun' },
  ent: { ko: '귀·코·목', en: 'Ear, nose, throat', vi: 'Tai, mũi, họng', roman: 'gwi, ko, mok', viPron: 'guy, cô, mốc' },
  teeth: { ko: '이·잇몸', en: 'Teeth, gums', vi: 'Răng, lợi', roman: 'i, in-mom', viPron: 'i, in-môm' },
  chest: { ko: '가슴', en: 'Chest', vi: 'Ngực', roman: 'ga-seum', viPron: 'ca-xưm' },
  abdomen: { ko: '배', en: 'Stomach', vi: 'Bụng', roman: 'bae', viPron: 'be' },
  back: { ko: '허리·등', en: 'Back, waist', vi: 'Lưng, eo', roman: 'heo-ri, deung', viPron: 'hơ-ri, tưng' },
  arm: { ko: '팔·어깨', en: 'Arm, shoulder', vi: 'Cánh tay, vai', roman: 'pal, eo-kkae', viPron: 'pan, ơ-ke' },
  hand: { ko: '손·손가락', en: 'Hand, finger', vi: 'Bàn tay, ngón tay', roman: 'son, son-ga-rak', viPron: 'xôn, xôn-ca-rác' },
  leg: { ko: '다리·무릎', en: 'Leg, knee', vi: 'Chân, đầu gối', roman: 'da-ri, mu-reup', viPron: 'ta-ri, mu-rứp' },
  foot: { ko: '발·발목', en: 'Foot, ankle', vi: 'Bàn chân, cổ chân', roman: 'bal, bal-mok', viPron: 'pan, pan-mốc' },
  skin: { ko: '피부', en: 'Skin', vi: 'Da', roman: 'pi-bu', viPron: 'pi-bu' },
  whole: { ko: '온몸', en: 'Whole body', vi: 'Toàn thân', roman: 'on-mom', viPron: 'ôn-môm' },
} satisfies Record<string, Term>;
export type BodyPart = keyof typeof BODY_PARTS;

// 증상 한국어 표기는 "~이/가 있습니다" 문장에 들어가도록 명사형으로 둔다.
export const SYMPTOMS = {
  pain: { ko: '통증', en: 'Pain', vi: 'Đau', roman: 'tong-jeung', viPron: 'thông-chưng' },
  swelling: { ko: '부기', en: 'Swelling', vi: 'Sưng', roman: 'bu-gi', viPron: 'bu-ghi' },
  cut: { ko: '베인 상처', en: 'Cut, wound', vi: 'Vết cắt, vết thương', roman: 'be-in sang-cheo', viPron: 'bê-in xang-chơ' },
  bleeding: { ko: '출혈', en: 'Bleeding', vi: 'Chảy máu', roman: 'chul-hyeol', viPron: 'chun-hiơn' },
  burn: { ko: '화상', en: 'Burn', vi: 'Bỏng', roman: 'hwa-sang', viPron: 'hoa-xang' },
  numb: { ko: '저림', en: 'Numbness', vi: 'Tê', roman: 'jeo-rim', viPron: 'chơ-rim' },
  cantmove: { ko: '움직이기 어려움', en: 'Hard to move', vi: 'Khó cử động', roman: 'um-ji-gi-gi eo-ryeo-um', viPron: 'um-chi-ghi-ghi ơ-riơ-um' },
  fever: { ko: '열', en: 'Fever', vi: 'Sốt', roman: 'yeol', viPron: 'iơn' },
  cough: { ko: '기침', en: 'Cough', vi: 'Ho', roman: 'gi-chim', viPron: 'ki-chim' },
  dizzy: { ko: '어지러움', en: 'Dizziness', vi: 'Chóng mặt', roman: 'eo-ji-reo-um', viPron: 'ơ-chi-rơ-um' },
  rash: { ko: '발진·가려움', en: 'Rash, itching', vi: 'Phát ban, ngứa', roman: 'bal-jin, ga-ryeo-um', viPron: 'pan-chin, ca-riơ-um' },
  nausea: { ko: '구토·메스꺼움', en: 'Nausea, vomiting', vi: 'Buồn nôn, nôn', roman: 'gu-to, me-seu-kkeo-um', viPron: 'cu-thô, mê-xư-cơ-um' },
  breath: { ko: '호흡 곤란', en: 'Hard to breathe', vi: 'Khó thở', roman: 'ho-heup gol-lan', viPron: 'hô-hứp côn-lan' },
  chemical: { ko: '화학물질 노출', en: 'Chemical exposure', vi: 'Tiếp xúc hóa chất', roman: 'hwa-hak-mul-jil no-chul', viPron: 'hoa-hác-mun-chin nô-chun' },
  foreign: { ko: '눈의 이물감', en: 'Something in the eye', vi: 'Dị vật trong mắt', roman: 'nu-ne i-mul-gam', viPron: 'nu-nê i-mun-cam' },
} satisfies Record<string, Term>;
export type Symptom = keyof typeof SYMPTOMS;

export const DEPARTMENTS = {
  ortho: { ko: '정형외과', en: 'Orthopaedics', vi: 'Chỉnh hình', roman: 'jeong-hyeong-oe-gwa', viPron: 'chơng-hiơng-uê-qua' },
  surgery: { ko: '외과', en: 'General surgery', vi: 'Ngoại khoa', roman: 'oe-gwa', viPron: 'uê-qua' },
  internal: { ko: '내과', en: 'Internal medicine', vi: 'Nội khoa', roman: 'nae-gwa', viPron: 'ne-qua' },
  ophth: { ko: '안과', en: 'Eye clinic', vi: 'Nhãn khoa', roman: 'an-gwa', viPron: 'an-qua' },
  ent: { ko: '이비인후과', en: 'ENT (ear, nose, throat)', vi: 'Tai mũi họng', roman: 'i-bi-in-hu-gwa', viPron: 'i-bi-in-hu-qua' },
  derm: { ko: '피부과', en: 'Dermatology (skin)', vi: 'Da liễu', roman: 'pi-bu-gwa', viPron: 'pi-bu-qua' },
  dental: { ko: '치과', en: 'Dentist', vi: 'Nha khoa', roman: 'chi-gwa', viPron: 'chi-qua' },
  neuro: { ko: '신경과', en: 'Neurology', vi: 'Thần kinh', roman: 'sin-gyeong-gwa', viPron: 'xin-ghiơng-qua' },
  family: { ko: '가정의학과', en: 'Family medicine', vi: 'Y học gia đình', roman: 'ga-jeong-ui-hak-gwa', viPron: 'ca-chơng-ưi-hác-qua' },
  occ: { ko: '직업환경의학과', en: 'Occupational medicine', vi: 'Y học nghề nghiệp', roman: 'ji-geop-hwan-gyeong-ui-hak-gwa', viPron: 'chi-gớp-hoan-ghiơng-ưi-hác-qua' },
} satisfies Record<string, Term>;
export type Department = keyof typeof DEPARTMENTS;

export const ONSETS = {
  today: { ko: '오늘', en: 'Today', vi: 'Hôm nay', roman: 'o-neul', viPron: 'ô-nưn' },
  yesterday: { ko: '어제', en: 'Yesterday', vi: 'Hôm qua', roman: 'eo-je', viPron: 'ơ-chê' },
  days: { ko: '2~3일 전', en: '2–3 days ago', vi: '2–3 ngày trước', roman: 'i-sam-il jeon', viPron: 'i-xam-in chơn' },
  week: { ko: '일주일 이상 전', en: 'Over a week ago', vi: 'Hơn một tuần trước', roman: 'il-ju-il i-sang jeon', viPron: 'in-chu-in i-xang chơn' },
} satisfies Record<string, Term>;
export type Onset = keyof typeof ONSETS;

export const INDUSTRIES = {
  shipbuilding: { ko: '조선', en: 'Shipbuilding', vi: 'Đóng tàu', roman: 'jo-seon', viPron: 'chô-xơn' },
  autoparts: { ko: '자동차 부품', en: 'Auto parts', vi: 'Phụ tùng ô tô', roman: 'ja-dong-cha bu-pum', viPron: 'cha-đông-cha bu-pum' },
  chemical: { ko: '화학', en: 'Chemical', vi: 'Hóa chất', roman: 'hwa-hak', viPron: 'hoa-hác' },
  construction: { ko: '건설', en: 'Construction', vi: 'Xây dựng', roman: 'geon-seol', viPron: 'cơn-xơn' },
  other: { ko: '기타', en: 'Other', vi: 'Khác', roman: 'gi-ta', viPron: 'ki-tha' },
} satisfies Record<string, Term>;
export type Industry = keyof typeof INDUSTRIES;

export const WORK_TYPES = {
  welding: { ko: '용접', en: 'Welding', vi: 'Hàn', roman: 'yong-jeop', viPron: 'iông-chớp' },
  lifting: { ko: '중량물 운반', en: 'Lifting, carrying', vi: 'Nâng, khuân vác', roman: 'jung-nyang-mul un-ban', viPron: 'chung-niang-mun un-ban' },
  machine: { ko: '기계(프레스 등) 작업', en: 'Machine work (press etc.)', vi: 'Vận hành máy (máy dập...)', roman: 'gi-gye jak-eop', viPron: 'ki-ghiê chác-ớp' },
  grinding: { ko: '절단·연마', en: 'Cutting, grinding', vi: 'Cắt, mài', roman: 'jeol-dan, yeon-ma', viPron: 'chơn-tan, iơn-ma' },
  painting: { ko: '도장·화학물질 취급', en: 'Painting, chemical handling', vi: 'Sơn, xử lý hóa chất', roman: 'do-jang', viPron: 'tô-chang' },
  assembly: { ko: '조립', en: 'Assembly', vi: 'Lắp ráp', roman: 'jo-rip', viPron: 'chô-ríp' },
} satisfies Record<string, Term>;
export type WorkType = keyof typeof WORK_TYPES;

export const DISTRICTS = {
  jung: { ko: '중구', en: 'Jung-gu', vi: 'Jung-gu', roman: 'jung-gu', viPron: 'chung-cu' },
  nam: { ko: '남구', en: 'Nam-gu', vi: 'Nam-gu', roman: 'nam-gu', viPron: 'nam-cu' },
  dong: { ko: '동구', en: 'Dong-gu', vi: 'Dong-gu', roman: 'dong-gu', viPron: 'tông-cu' },
  buk: { ko: '북구', en: 'Buk-gu', vi: 'Buk-gu', roman: 'buk-gu', viPron: 'búc-cu' },
  ulju: { ko: '울주군', en: 'Ulju-gun', vi: 'Ulju-gun', roman: 'ul-ju-gun', viPron: 'un-chu-cun' },
} satisfies Record<string, Term>;
export type District = keyof typeof DISTRICTS;

export type YesNoUnknown = 'yes' | 'no' | 'unknown';

export const LANGUAGE_NAMES_KO: Record<Lang, string> = { en: '영어', vi: '베트남어' };

/** 한국어 단어 끝 받침 여부에 따라 조사를 고른다(이/가, 은/는 등). */
export function josa(word: string, withBatchim: string, withoutBatchim: string): string {
  const last = word.trim().at(-1) ?? '';
  const code = last.charCodeAt(0) - 0xac00;
  if (code < 0 || code > 11171) return word + withoutBatchim;
  return word + (code % 28 === 0 ? withoutBatchim : withBatchim);
}
