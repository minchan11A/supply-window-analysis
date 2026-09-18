const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  WidthType, AlignmentType, BorderStyle, ShadingType, HeadingLevel,
  ImageRun, VerticalAlign, PageNumber, Header, Footer,
} = require('docx');
const fs = require('fs');

const FONT = 'Noto Sans CJK KR';
const NAVY = '0B3D91';
const GRAY = '595959';

// ─── helpers ───────────────────────────────────────────────
const P = (text, o = {}) => new Paragraph({
  alignment: o.align || AlignmentType.LEFT,
  spacing: { before: o.before ?? 40, after: o.after ?? 60, line: o.line ?? 264 },
  indent: o.indent ? { left: o.indent } : undefined,
  border: o.border,
  children: [new TextRun({
    text, font: FONT, size: o.size || 19, bold: o.bold || false,
    color: o.color || '000000', italics: o.italics || false,
  })],
});

// rich paragraph: array of [text, {bold,color,size}]
const RP = (runs, o = {}) => new Paragraph({
  alignment: o.align || AlignmentType.LEFT,
  spacing: { before: o.before ?? 40, after: o.after ?? 60, line: o.line ?? 264 },
  indent: o.indent ? { left: o.indent } : undefined,
  children: runs.map(([t, s = {}]) => new TextRun({
    text: t, font: FONT, size: s.size || o.size || 19,
    bold: s.bold || false, color: s.color || '000000', italics: s.italics || false,
  })),
});

// 대제목 (1. 개요 등)
const H1 = (text) => new Paragraph({
  spacing: { before: 200, after: 90 },
  border: { bottom: { style: BorderStyle.SINGLE, size: 10, color: NAVY, space: 3 } },
  children: [new TextRun({ text, font: FONT, size: 23, bold: true, color: NAVY })],
});

// 중제목 (가. 나.)
const H2 = (text) => new Paragraph({
  spacing: { before: 130, after: 55 },
  children: [new TextRun({ text, font: FONT, size: 20, bold: true, color: '14488C' })],
});

// 본문 불릿  (1) (2)
const B = (text, o = {}) => RP(
  [[o.marker ?? '', { bold: true, color: NAVY }], [text]],
  { indent: o.indent ?? 240, after: 45 }
);

const cell = (children, o = {}) => new TableCell({
  width: { size: o.w, type: WidthType.DXA },
  columnSpan: o.span,
  rowSpan: o.rowSpan,
  verticalAlign: VerticalAlign.CENTER,
  shading: o.fill ? { type: ShadingType.CLEAR, fill: o.fill, color: 'auto' } : undefined,
  margins: { top: 60, bottom: 60, left: 90, right: 90 },
  children,
});

const tcell = (text, o = {}) => cell(
  [new Paragraph({
    alignment: o.align || AlignmentType.CENTER,
    spacing: { before: 0, after: 0, line: 240 },
    children: [new TextRun({
      text, font: FONT, size: o.size || 17,
      bold: o.bold || false, color: o.color || '000000',
    })],
  })],
  o
);

const img = (file, w, h) => new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { before: 100, after: 60 },
  children: [new ImageRun({
    type: 'png', data: fs.readFileSync(file),
    transformation: { width: w, height: h },
  })],
});

const caption = (text) => P(text, {
  align: AlignmentType.CENTER, size: 15, color: GRAY, italics: true, after: 130,
});

const note = (text) => new Paragraph({
  spacing: { before: 70, after: 90, line: 252 },
  indent: { left: 120 },
  border: { left: { style: BorderStyle.SINGLE, size: 14, color: 'E0A800', space: 8 } },
  shading: { type: ShadingType.CLEAR, fill: 'FFFBF0', color: 'auto' },
  children: [new TextRun({ text, font: FONT, size: 17, color: '5A4A1A' })],
});

// ─── 표지 상단: 주제명 / 공모분야 / 참가자 ──────────────────
const TW = 9600;
const headerTable = new Table({
  width: { size: TW, type: WidthType.DXA },
  columnWidths: [1500, 8100],
  rows: [
    new TableRow({ children: [
      tcell('주 제 명', { w: 1500, bold: true, fill: 'DCE6F2' }),
      tcell('도서·격오지 부대 보급 안전재고 기준의 데이터 기반 재설정 및 선제보급 판단절차 도입 방안',
            { w: 8100, align: AlignmentType.LEFT, bold: true, size: 19, color: NAVY }),
    ]}),
    new TableRow({ children: [
      tcell('공모\n분야', { w: 1500, bold: true, fill: 'DCE6F2' }),
      cell([
        new Paragraph({ spacing: { before: 0, after: 0, line: 240 }, children: [
          new TextRun({ text: '앱/웹서비스  (    )        ', font: FONT, size: 17 }),
          new TextRun({ text: '정책/아이디어  ( √ )', font: FONT, size: 17, bold: true, color: NAVY }),
        ]}),
      ], { w: 8100 }),
    ]}),
  ],
});

const participantTable = new Table({
  width: { size: TW, type: WidthType.DXA },
  columnWidths: [1500, 1700, 1300, 1400, 3700],
  rows: [
    new TableRow({ children: [
      tcell('구 분', { w: 1500, bold: true, fill: 'DCE6F2' }),
      tcell('소 속', { w: 1700, bold: true, fill: 'DCE6F2' }),
      tcell('계급/직급', { w: 1300, bold: true, fill: 'DCE6F2' }),
      tcell('성 명', { w: 1400, bold: true, fill: 'DCE6F2' }),
      tcell('연 락 처', { w: 3700, bold: true, fill: 'DCE6F2' }),
    ]}),
    new TableRow({ children: [
      tcell('참가자\n(팀명       )', { w: 1500 }),
      tcell('', { w: 1700 }),
      tcell('', { w: 1300 }),
      tcell('', { w: 1400 }),
      cell([
        P('(군)', { size: 16, after: 0 }),
        P('(휴대전화)', { size: 16, after: 0 }),
        P('(이메일)', { size: 16, after: 0 }),
      ], { w: 3700 }),
    ]}),
  ],
});

// ─── 범용 표 생성기 ─────────────────────────────────────────
const dataTable = (widths, header, rows, opts = {}) => {
  const total = widths.reduce((a, b) => a + b, 0);
  return new Table({
    width: { size: total, type: WidthType.DXA },
    columnWidths: widths,
    rows: [
      new TableRow({
        tableHeader: true,
        children: header.map((h, i) =>
          tcell(h, { w: widths[i], bold: true, color: 'FFFFFF', fill: NAVY, size: 16 })),
      }),
      ...rows.map((r, ri) => new TableRow({
        children: r.map((c, i) => {
          const isBold = opts.boldCols?.includes(i);
          return tcell(String(c), {
            w: widths[i], size: 16, bold: isBold,
            color: isBold ? NAVY : '000000',
            fill: ri % 2 === 1 ? 'F4F7FB' : undefined,
            align: i === 0 && opts.leftFirst ? AlignmentType.LEFT : AlignmentType.CENTER,
          });
        }),
      })),
    ],
  });
};

// ═══════════════════════════════════════════════════════════
const body = [];

body.push(P('붙임 #3', { size: 16, color: GRAY, after: 80 }));
body.push(headerTable);
body.push(P('', { after: 0, size: 8 }));
body.push(participantTable);

// ─── 1. 개요 ────────────────────────────────────────────────
body.push(H1('1. 개 요'));
body.push(note(
  '한 줄 요약 : 도서·격오지 부대의 보급 제약은 통념과 달리 강풍이 아니라 시정(視程) 불량이 지배하며, ' +
  '현행 획일적 안전재고 기준을 10년 관측자료 기반의 부대별 차등 기준으로 재설정해야 한다.'
));
body.push(RP([
  ['본 제안은 신규 장비·시스템 도입 없이, '],
  ['공개된 기상 관측 데이터', { bold: true }],
  ['를 분석하여 '],
  ['이미 운용 중인 보급 체계의 기준값을 교정', { bold: true }],
  ['하는 정책 제안이다. 서해 백령도 ASOS 10년치(87,432시간) 전수 분석을 통해 다음 3가지를 도출하였다.'],
]));
body.push(dataTable(
  [900, 3200, 5500],
  ['구분', '핵심 발견', '근 거'],
  [
    ['①', '제약 요인의 재발견', '선박 운용불가의 94.9%, 헬기의 97.2%가 시정 불량 기인 (강풍은 각 4.2%, 1.3%)'],
    ['②', '수단 간 상보성 실증', '드론 불가일의 84.7%는 선박·헬기 중 1개 이상 운용 가능 (드론만 풍속이 주 제약 61.9%)'],
    ['③', '위험 시기의 재발견', '전수단 동시불가 15일 중 7월이 5일로 최다 — 동절기가 아닌 하계 해무철 집중'],
    ['④', '기준값의 교차 검증', 'P95 방식과 복합 포아송-기하 재현기간 분석이 동일하게 3일분 도출 (20년 재현수준)'],
  ],
  { boldCols: [1] }
));
body.push(H2('◇ 제안 내용'));
body.push(B('부대별 차등 안전재고 기준표 도입 (백령도 산출값 : 3일분)', { marker: '(1) ' }));
body.push(B('선제보급 판단절차(SOP) 신설 — 시스템 없이 종이 체크리스트로 즉시 시행 가능', { marker: '(2) ' }));
body.push(B('시정 중심 보급계획 전환 — 현행 풍랑특보 중심 관행의 보완', { marker: '(3) ' }));
body.push(RP([
  ['※ 사용 데이터는 '],
  ['전량 공개 데이터', { bold: true }],
  ['(기상자료개방포털)로 보안 제약이 없으며, 분석 코드는 공개되어 재현 가능하다.'],
], { size: 17, indent: 240 }));
body.push(note(
  '왜 지금인가 : 2019년 이후 관측상 전수단 동시 고립은 발생하지 않았다. 그러나 이는 "위험이 사라졌다"가 ' +
  '아니라 "사건이 특정 연도에 몰아서 발생하는 패턴(2-나항 참조)에서 현재 평온기에 있다"는 의미이다. ' +
  '안전재고 기준은 평시 부재가 아니라 다음 몰림에 대한 대비이며, 평온기가 곧 기준을 정비할 적기이다.'
));

// ─── 2. 제안배경 ────────────────────────────────────────────
body.push(H1('2. 제안배경'));
body.push(H2('가. 현 실태'));
body.push(RP([
  ['서해 5도 등 도서·산간 격오지 부대는 기상 악화 시 보급이 중단되며, 이는 단순한 불편이 아니라 '],
  ['전투지속능력의 직접적 저하', { bold: true }],
  ['로 이어진다. 현행 체계에는 다음 3가지 공백이 존재한다.'],
]));
body.push(RP([
  ['(1) 안전재고 기준의 획일성 ', { bold: true, color: NAVY }],
  ['— 현행 기준은 부대별 실제 고립 위험과 무관하게 적용된다. 위험이 낮은 부대는 과다 재고로 예산이 묶이고, 높은 부대는 과소 재고로 고립에 노출되는 '],
  ['양방향 비효율', { bold: true }],
  ['이 발생한다.'],
], { indent: 240, after: 55 }));
body.push(RP([
  ['(2) 판단 기준의 부재 ', { bold: true, color: NAVY }],
  ['— "며칠 뒤 얼마나 나빠질 때 지금 선제보급을 해야 하는가"를 판단할 정량 기준이 없어, 보급은 기상 악화 '],
  ['이후', { bold: true }],
  [' 대응하는 사후적 성격을 띤다.'],
], { indent: 240, after: 55 }));
body.push(RP([
  ['(3) 제약 요인에 대한 오인 ', { bold: true, color: NAVY }],
  ['— 보급 중단의 주 원인을 강풍·풍랑으로 인식하는 관행이 있으나, 본 분석은 이것이 '],
  ['사실과 다름', { bold: true }],
  ['을 보여준다(3-나항).'],
], { indent: 240 }));

body.push(H2('나. 분석 필요성'));
body.push(RP([
  ['위 3가지 공백은 모두 '],
  ['"데이터로 확인된 적이 없다"', { bold: true }],
  ['는 하나의 원인에서 비롯된다. 어느 부대가 연중 며칠이나 고립되는지, 무엇이 실제로 보급을 막는지, ' +
   '어느 시기가 가장 위험한지에 대한 정량적 근거가 부재한 상태에서 기준과 관행이 형성되어 왔다.'],
]));
body.push(RP([
  ['반면 이를 판단할 데이터는 '],
  ['이미 10년 이상 공개되어 축적', { bold: true }],
  ['되어 있다. 본 제안은 그 데이터를 분석하여 기준의 근거를 마련하고자 한다.'],
]));

body.push(H2('다. 왜 지금 준비해야 하는가 — 평온기와 대비의 관계'));
body.push(RP([
  ['본 분석 결과 2019년 이후 관측상 전수단 동시 고립은 발생하지 않았다. 이 사실은 '],
  ['"안전재고 기준이 불필요하다"가 아니라 오히려 그 반대를 시사한다.', { bold: true }],
]));
body.push(B(
  '사건은 몰아서 온다 — 3-다-(4)항 포아송 사건빈도 분석 결과 과산포지수 2.93으로, 고립사건은 ' +
  '평년에 고르게 분포하지 않고 특정 연도에 집중된다(2016년 5건, 2018년 4건). 7년의 평온기는 ' +
  '위험 소멸의 증거가 아니라, 해당 패턴상 나타나는 자연스러운 휴지기이다.',
  { marker: '(1) ' }
));
body.push(B(
  '감소 추세는 확인되나 기준 완화 근거로 삼지 않는다 — Mann-Kendall 검정에서 고립일수 감소가 ' +
  '통계적으로 유의(p=0.011)하게 나타났다. 그러나 표본이 10개년에 불과해 이 추세가 기후 변화, ' +
  '관측 방식 변화, 우연 중 무엇에 기인하는지 판별할 수 없다. 안전 관련 기준에서 최근의 호조를 ' +
  '근거로 대비 수준을 낮추는 것은 신중하지 않다.',
  { marker: '(2) ' }
));
body.push(B(
  '평온기는 기준 정비의 최적 시점이다 — 위기 상황에서 처음 기준을 만들면 이미 늦다. ' +
  '안전재고 기준·판단절차는 화재가 없을 때 소화기를 비치하는 것과 같은 성격의 상시 대비 조치이며, ' +
  '데이터가 안정적인 지금이 제도화의 적기이다.',
  { marker: '(3) ' }
));

// ─── 3. 주요내용 ────────────────────────────────────────────
body.push(H1('3. 주요내용'));
body.push(H2('가. 활용 데이터 및 선정 배경'));
body.push(dataTable(
  [1700, 7900],
  ['항 목', '내 용'],
  [
    ['출처', '기상청 기상자료개방포털(data.kma.go.kr) 종관기상관측(ASOS) 시간자료'],
    ['관측지점', '백령도(지점번호 102) — 서해 최북단 도서, 격오지 보급 환경의 대표 사례'],
    ['기간 / 표본', '2016.01.01 ~ 2025.12.31 (10년) / 87,432 시간 레코드 → 전처리 후 3,643일'],
    ['변수', '풍속(m/s), 시정(10m), 강수량(mm)'],
    ['보안', '전량 공개 데이터 — 군사자료 미포함, 인트라넷 반입 제약 없음'],
  ],
  { boldCols: [0], leftFirst: false }
));
body.push(RP([
  ['ASOS를 선정한 이유는 '], ['시정 관측 여부', { bold: true }],
  ['에 있다. 도서·산간에 조밀하게 설치된 AWS(방재기상관측)는 대부분 시정을 관측하지 않는 반면, ' +
   'ASOS는 시정을 포함한 전요소를 정규 관측한다. 분석 결과 시정이 보급 제약의 지배 요인으로 확인되어, 이 선택이 결정적이었다.'],
]));

body.push(H2('나. 분석 방법'));
body.push(RP([
  ['본 분석은 '], ['머신러닝 예측모델을 사용하지 않는다.', { bold: true }],
  [' 과거 보급 실적이 정형 DB로 존재하지 않는 현실(Cold Start)에서 검증 불가능한 예측 확률을 제시하는 것은 ' +
   '오히려 신뢰를 훼손하기 때문이다. 대신 '],
  ['학습 데이터 없이도 엄밀성이 확보되는 확률·통계 기법', { bold: true }],
  ['을 적용하였다. 구체적으로 마르코프 지속성 추정, 포아송 사건빈도 모형, 복합 포아송-기하 분포에 의한 ' +
   '재현기간 산출, 부트스트랩 신뢰구간, Mann-Kendall 비모수 추세검정, φ계수 기반 의존구조 검정을 사용하였다. ' +
   '이는 수문·방재 분야에서 확률강우량과 계획홍수위를 정할 때 쓰는 표준 방법론과 동일한 계열이다.'],
]));
body.push(dataTable(
  [1900, 3000, 4700],
  ['단 계', '질 문', '산출 내용'],
  [
    ['1단계 기술통계', '무슨 일이 있었는가', '수단별 가용률, 고립일수, 월별·연도별 분포'],
    ['2단계 진단분석', '왜 그런 패턴이 나오는가', '원인 분해(풍속/시정/강수), 계절성, 수단 간 의존구조 검정(φ계수·χ²)'],
    ['3단계 통계추론', '얼마나 확실한가', '마르코프 지속성·포아송 빈도·복합모형 재현수준·부트스트랩 CI·Mann-Kendall 추세검정'],
    ['4단계 처방로직', '기준을 어떻게 정할 것인가', '재현기간 및 백분위 기반 안전재고 산정 (예측모델 아님)'],
  ],
  { boldCols: [0] }
));
body.push(P('◇ 판정 기준 (운용 임계값)', { bold: true, color: '14488C', before: 130, after: 55, size: 20 }));
body.push(dataTable(
  [1600, 1900, 1900, 1900],
  ['수 단', '한계풍속', '최소시정', '최대강수'],
  [
    ['선박', '14.0 m/s', '1,000 m', '15 mm/h'],
    ['헬기', '15.0 m/s', '1,600 m', '10 mm/h'],
    ['드론', '8.0 m/s', '500 m', '3 mm/h'],
  ],
  { boldCols: [0] }
));
body.push(note(
  '본 임계값은 일반적 운용기준을 참조한 예시값이다. 실제 적용 시 해당 부대의 운용교범·장비 제원으로 ' +
  '대체해야 한다. 다만 3-다항 (4) 민감도 분석을 통해, 임계값을 양방향으로 조정하여도 핵심 결론이 유지됨을 검증하였다.'
));
body.push(RP([
  ['◇ 지표 정의 : ', { bold: true, color: '14488C' }],
  ['운용가능일 = 해당 수단의 운용 조건을 만족하는 시간대가 하루 중 6시간 이상인 날 / ' +
   '전수단 동시불가일 = 3개 수단이 모두 불가한 날 / 최장 연속 고립일수 = 동시불가일의 최대 연속 구간'],
], { size: 17 }));
body.push(RP([
  ['◇ 전처리 : ', { bold: true, color: '14488C' }],
  ['① 강수량 공란은 측정 실패가 아닌 무강수를 의미하므로 0으로 처리. ' +
   '② 일 관측 레코드가 18시간 미만인 날은 제외(총 10일). 포털의 연도별 다운로드 구조상 각 연도 말일에 관측치가 ' +
   '1시간만 존재하여, 미보정 시 '],
  ['기상과 무관하게 운용불가로 오판정', { bold: true }],
  ['되는 문제가 발생(보정 전 고립사건 22건 중 10건이 이 인공 산물).'],
], { size: 17 }));

body.push(H2('다. 분석 결과'));
body.push(P('(1) 보급을 막는 것은 강풍이 아니라 안개다', { bold: true, color: NAVY, size: 20, before: 100, after: 55 }));
body.push(img('04_limiting_factor_breakdown.png', 500, 233));
body.push(caption('[그림 1] 수단별 운용불가 원인 분해 (10년 누적)'));
body.push(dataTable(
  [1600, 2300, 2300, 2300],
  ['수 단', '시정 불량', '평균풍속 초과', '강수 과다'],
  [
    ['선박', '94.9 %', '4.2 %', '1.3 %'],
    ['헬기', '97.2 %', '1.3 %', '2.3 %'],
    ['드론', '34.0 %', '61.9 %', '6.7 %'],
  ],
  { boldCols: [0] }
));
body.push(RP([
  ['백령도 10년 관측에서 풍속이 선박 한계(14m/s)를 초과한 시간은 전체의 '],
  ['0.3%', { bold: true }],
  ['에 불과한 반면, 시정 1,000m 미만은 '],
  ['9.1%', { bold: true }],
  ['였다. 풍랑특보를 주 지표로 삼는 관행은 실제 제약의 4% 수준만 반영하는 셈이다.'],
]));

body.push(P('(2) 수단 간 상보성 — 다중수단 운용의 실증적 근거', { bold: true, color: NAVY, size: 20, before: 130, after: 55 }));
body.push(dataTable(
  [2600, 2200, 3200],
  ['불가 수단', '불가일수', '대체수단 가용 비율'],
  [
    ['드론 불가 시', '98일', '84.7 %'],
    ['헬기 불가 시', '34일', '55.9 %'],
    ['선박 불가 시', '24일', '37.5 %'],
  ],
  { boldCols: [2] }
));
body.push(RP([
  ['드론은 풍속에, 선박·헬기는 시정에 각각 취약하다는 '],
  ['제약 구조의 비대칭성', { bold: true }],
  ['이 상보성의 원인이다. 즉 "기상이 나쁘다"는 단일 판단으로 전 수단을 일괄 중단하는 것은 ' +
   '가용한 보급 기회를 상실하는 것이다.'],
]));

body.push(P('(3) 고립 위험의 정량화', { bold: true, color: NAVY, size: 20, before: 130, after: 55 }));
body.push(img('01_monthly_availability_heatmap.png', 530, 153));
body.push(caption('[그림 2] 월별 × 수단별 운용 가용률 (연평균 : 선박 99.3% / 헬기 99.1% / 드론 97.3%)'));
body.push(RP([
  ['전수단 동시불가일은 '],
  ['15일 / 3,643일 (0.41%)', { bold: true }],
  ['이며, 월별로는 7월 5일 · 5월 3일 · 2~4월 각 2일 · 8월 1일로 '],
  ['하계 해무철에 집중', { bold: true }],
  ['된다. 10년간 최장 연속 고립은 '],
  ['2일', { bold: true }],
  ['(총 12건의 고립사건)이었다. 연도별로는 2016년 7일에서 2019년 이후 연 0~1일로 감소 추세가 관찰되나, ' +
   '이는 3-다-(4)항 과산포 분석에서 확인되듯 사건이 특정 연도에 집중되는 패턴(2016년 5건, 2018년 4건)의 ' +
   '결과이지 위험의 소멸이 아니다. 따라서 안전재고 기준은 보수적으로 과거 최악값을 반영함이 타당하다.'],
]));

body.push(P('(4) 민감도 분석 — 결론의 강건성 검증', { bold: true, color: NAVY, size: 20, before: 130, after: 55 }));
body.push(RP([
  ['"임계값을 자의적으로 설정한 것 아닌가"라는 문제제기에 대응하기 위해, 임계값을 '],
  ['보수적·완화 양방향으로 조정', { bold: true }],
  ['하여 결론이 유지되는지 검증하였다.'],
]));
body.push(img('05_sensitivity_analysis.png', 535, 172));
body.push(caption('[그림 3] 임계값 시나리오별 원인 기여도 및 권고 안전재고'));
body.push(dataTable(
  [2900, 1700, 1600, 1800, 1600],
  ['시나리오', '선박 가용률', '동시불가', '선박 시정기인', '권고 안전재고'],
  [
    ['기준 (Baseline)', '99.3 %', '15일', '94.9 %', '3일분'],
    ['보수적 (풍속 −20%, 시정 ×1.5)', '98.9 %', '25일', '79.6 %', '3일분'],
    ['완화 (풍속 +20%, 시정 ×0.7)', '99.6 %', '9일', '98.9 %', '3일분'],
    ['시정만 강화 (×2)', '99.0 %', '26일', '96.5 %', '4일분'],
    ['풍속만 강화 (−30%)', '98.5 %', '30일', '61.5 %', '3일분'],
  ],
  { boldCols: [3, 4], leftFirst: true }
));
body.push(RP([
  ['풍속 기준을 '], ['30% 더 엄격하게', { bold: true }],
  [' 조여 풍속의 영향을 최대한 부각시킨 시나리오에서도 선박 운용불가의 '],
  ['61.5%는 여전히 시정에 기인', { bold: true }],
  ['한다. 권고 안전재고 또한 5개 시나리오 중 4개에서 3일분으로 동일하여, '],
  ['3~4일분 범위가 합리적 기준', { bold: true }],
  ['임이 확인된다.'],
]));

body.push(P('(5) 통계적 추론 — 안전재고 기준의 엄밀화', { bold: true, color: NAVY, size: 20, before: 130, after: 55 }));
body.push(RP([
  ['백분위수만으로는 표본 10개년의 불확실성을 다룰 수 없다. 이에 '],
  ['고립의 빈도구조 자체를 모형화', { bold: true }],
  ['하여 재현기간(return period)별 수준을 산출하였다. 이는 수문·방재 분야에서 확률강우량·계획홍수위를 ' +
   '정하는 것과 동일한 표준 기법이며, 미래를 예측하는 것이 아니라 '],
  ['관측된 빈도구조 하의 극단 수준을 추정', { bold: true }],
  ['하는 것이다.'],
]));
body.push(dataTable(
  [2300, 1500, 5800],
  ['분석', '결과', '해석'],
  [
    ['① 마르코프 지속성', 'p = 0.200', '고립 시작 후 다음 날도 고립일 조건부 확률 20.0%. 평균 1.25일 만에 해소되어 장기화 경향은 약함 (사건 12건 / 총 15일)'],
    ['② 포아송 사건빈도', 'λ = 1.20', '연평균 1.2회 발생. 과산포지수 2.93으로 분산이 평균을 크게 상회 → 사건이 특정 연도에 군집하므로 평년이 아닌 극단 연도 기준 대비 필요'],
    ['③ 부트스트랩 95% CI', '[1.0, 2.0]일', 'P95 점추정 2.0일의 신뢰구간. 소표본 불확실성이 존재하므로 상한 고려한 보수적 설정이 타당'],
    ['④ Mann-Kendall 추세', 'p = 0.011', '고립일수 감소 추세가 통계적으로 유의(Sen 기울기 −0.33일/년). 다만 안전 측면에서 이를 기준 완화 근거로 삼지 않고 전 기간을 동등 반영'],
  ],
  { boldCols: [1], leftFirst: true }
));
body.push(P('◇ 복합 포아송-기하 모형에 의한 재현수준', { bold: true, color: '14488C', before: 110, after: 50, size: 19 }));
body.push(RP([
  ['연간 사건수 N ~ Poisson(λ), 각 사건 지속일수 D ~ Geometric(1−p)로 두면, 포아송 희박화(thinning) 성질에 의해 ' +
   '연최대 고립일수 M의 분포는 P(M < k) = exp(−λ · p^(k−1)) 로 유도된다. ' +
   '이로부터 재현기간별 수준을 산출한 결과는 다음과 같다.'],
], { size: 17 }));
body.push(dataTable(
  [2000, 1900, 1900, 1900, 1900],
  ['재현기간', '5년', '10년', '20년', '50년'],
  [['고립 수준', '3일', '3일', '3일', '4일']],
  { boldCols: [3] }
));
body.push(img('06_return_level.png', 420, 228));
body.push(caption('[그림 4] 재현기간별 고립 수준 — 권고 3일분이 20년 재현수준과 일치'));
body.push(note(
  '핵심 : 앞서 P95 방식으로 도출한 3일분이, 전혀 다른 경로인 재현기간 분석에서도 20년 재현수준(초과확률 4.7%)과 ' +
  '정확히 일치한다. 두 독립적 방법이 동일 결론에 수렴함으로써 기준값의 타당성이 교차 검증되었다.'
));

body.push(P('(6) 수단 간 상보성의 통계적 검정', { bold: true, color: NAVY, size: 20, before: 130, after: 55 }));
body.push(RP([
  ['3-다-(2)항의 상보성이 우연인지 구조적인지 확인하기 위해 수단 쌍별 의존구조를 검정하였다. ' +
   '독립 가정 하의 기대 동시불가일수 대비 관측값의 비(比)를 보면:'],
]));
body.push(dataTable(
  [1800, 2100, 2100, 1900, 1700],
  ['수단쌍', '독립가정 기대', '실제 관측', '관측/기대', 'φ계수'],
  [
    ['선박–헬기', '0.2일', '24일', '107.2배', '0.821'],
    ['선박–드론', '0.6일', '15일', '23.2배', '0.291'],
    ['헬기–드론', '0.9일', '15일', '16.4배', '0.240'],
  ],
  { boldCols: [3], leftFirst: false }
));
body.push(RP([
  ['선박–헬기는 φ=0.821로 '],
  ['강한 동조', { bold: true }],
  ['를 보인다. 둘 다 시정에 지배되므로 함께 막히는 것이다. 반면 드론과의 쌍은 φ=0.24~0.29로 '],
  ['현저히 약한 동조', { bold: true }],
  ['를 보이며, 이는 드론만 풍속이 주 제약(61.9%)이기 때문이다. 즉 '],
  ['상보성은 우연이 아니라 제약 요인이 서로 다른 데서 오는 구조적 성질', { bold: true }],
  ['이며(모든 쌍 p<0.001), 다중수단 운용의 통계적 근거가 된다.'],
]));

body.push(P('(7) 지형 대표성 민감도 — 관측소가 부대를 대표하지 못한다면', { bold: true, color: NAVY, size: 20, before: 130, after: 55 }));
body.push(RP([
  ['관측소와 실제 부대(해안 절벽·산악) 간 국지풍 차이는 실재한다. 본 제안은 이를 수치표고모델(DEM)로 '],
  ['보정하지 않는다', { bold: true }],
  ['. 검증되지 않은 보정값은 자산이 아니라 부채이기 때문이다. 대신 '],
  ['"부대 실제 풍속이 관측소보다 X% 높다면 결론이 어떻게 바뀌는가"', { bold: true }],
  ['를 정량 추적하여 같은 우려에 답하였다.'],
]));
body.push(img('07_terrain_sensitivity.png', 430, 220));
body.push(caption('[그림 5] 지형 대표성 민감도 — 풍속 가정별 수단 가용률 변화'));
body.push(dataTable(
  [2400, 1700, 1700, 1700, 2100],
  ['풍속 가정', '선박', '헬기', '드론', '최장 고립일'],
  [
    ['관측소 대비 +0%', '99.3 %', '99.1 %', '97.3 %', '2일'],
    ['관측소 대비 +10%', '99.3 %', '99.1 %', '96.0 %', '2일'],
    ['관측소 대비 +20%', '99.2 %', '99.0 %', '94.7 %', '2일'],
    ['관측소 대비 +30%', '99.1 %', '98.9 %', '93.4 %', '2일'],
  ],
  { boldCols: [4], leftFirst: false }
));
body.push(RP([
  ['풍속을 30%까지 상향해도 '],
  ['선박·헬기 가용률은 0.2%p 변화에 그치고, 최장 고립일수는 2일로 불변', { bold: true }],
  ['이다. 지형에 의한 풍속 과소평가가 있더라도 '],
  ['안전재고 기준은 영향받지 않는다', { bold: true }],
  ['. 다만 드론 가용률은 97.3%→93.4%로 3.9%p 하락하므로, '],
  ['드론을 주 수단으로 운용하는 부대는 현장 풍속 실측이 필요', { bold: true }],
  ['하다는 점이 함께 도출된다.'],
]));

body.push(H2('라. 제안 (1) — 부대별 차등 안전재고 기준표'));
body.push(RP([
  ['◇ 산정 근거 : ', { bold: true, color: '14488C' }],
  ['① P95(연도별 최장 연속 고립일수) + 안전마진 1일 = 3일분, ' +
   '② 복합 포아송-기하 모형의 20년 재현수준 = 3일 — '],
  ['두 독립 방법이 동일 결론', { bold: true }],
]));
body.push(RP([
  ['평균 최장 고립일수는 0.6일이지만, 이를 기준으로 재고를 맞추면 기상이 특히 나빴던 해(2016년 7일 고립)에는 ' +
   '재고가 바닥난다. 안전재고의 목적은 평년 대응이 아니라 '],
  ['극단 상황 대응', { bold: true }],
  ['이므로, 분포의 꼬리(tail)를 기준으로 삼아야 한다. 과산포지수 2.93은 사건이 특정 연도에 군집함을 ' +
   '보여주어 이 논리를 뒷받침한다.'],
]));
body.push(note(
  '안전마진 1일의 근거 : 본 분석은 기상 조건상 운용 가능 여부만을 판정하므로, 정비·인력·행정 사유로 인한 ' +
  '보급 무산은 포착하지 못한다. 반대로 기상이 막는데 보급이 성공하는 경우는 드물다. 따라서 산출된 고립일수는 ' +
  '실제 고립 위험의 하한(lower bound)이며, 안전마진 1일은 이 편향 방향을 보정하는 조치이다.'
));
body.push(P('[별표(안)] 도서·격오지 부대 보급 안전재고 기준', { bold: true, size: 18, before: 110, after: 55 }));
body.push(dataTable(
  [1900, 1600, 1500, 1500, 1500, 1600],
  ['부대 구분', '관측지점', '분석기간', '연간 가용률', 'P95 최장고립', '권고 안전재고'],
  [
    ['백령도 지역', '백령도(102)', '2016~2025', '99.3 %', '2일', '3일분'],
    ['(타 부대)', '(인근 ASOS)', '(10년)', '(산출)', '(산출)', '(산출)'],
  ],
  { boldCols: [5] }
));
body.push(RP([
  ['본 제안의 분석 코드는 공개되어 있으며, 대상 부대 인근 관측지점 데이터를 입력하면 '],
  ['동일 방법론으로 즉시 산출 가능', { bold: true }],
  ['하다. 전군 도서·격오지 부대로 확대 적용 시 위 별표를 완성할 수 있다.'],
], { size: 17 }));
body.push(P('◇ 계절별 차등 적용 (선택 강화안)', { bold: true, color: '14488C', before: 110, after: 55, size: 19 }));
body.push(dataTable(
  [2200, 4400, 3000],
  ['구 분', '적용 기간', '안전재고'],
  [
    ['평시 / 주의기', '9~11월, 1월 / 2~5월', '기준값'],
    ['위험기', '6~8월(해무기), 12월(강풍기)', '기준값 + 1일분'],
  ],
  { boldCols: [2] }
));

body.push(H2('마. 제안 (2) — 선제보급 판단절차(SOP)'));
body.push(P('시스템 구축 없이, 종이 체크리스트만으로 즉시 시행 가능하다.', { bold: true, after: 70 }));

const sopRows = [
  ['STEP 1', '기상 확인', '향후 72시간 시정 예보 확인  ← 1차 지표 / 풍속 예보 확인'],
  ['STEP 2', '수단별 가용성 판단', '선박 : 시정 1,000m↑ 풍속 14m/s↓ · 헬기 : 시정 1,600m↑ 풍속 15m/s↓ · 드론 : 풍속 8m/s↓ 시정 500m↑ → 최소 1개 가용 시 "보급 가능"'],
  ['STEP 3', '재고 대비 확인', '현 재고 잔여일수 (      )일  vs  권고 안전재고 ( 3 )일'],
  ['STEP 4', '판 단', '재고 < 안전재고 AND 금일 보급 가능 → 선제보급 실시(지휘관 결심) / 48시간 내 전 수단 제한 예상 → 선제보급 검토 / 그 외 → 정상'],
];
body.push(dataTable([1300, 2300, 6000], ['단계', '확인 사항', '판단 기준'], sopRows, { boldCols: [0], leftFirst: false }));
body.push(P('◇ 절차의 핵심 원칙', { bold: true, color: '14488C', before: 110, after: 55, size: 19 }));
body.push(dataTable(
  [2600, 7000],
  ['원 칙', '내 용'],
  [
    ['최종 결정은 지휘관', '본 절차는 판단 보조 수단이며, 알고리즘이 보급을 결정하지 않는다'],
    ['근거 병기', '모든 판정에 "왜 불가한가"(시정/풍속/강수)를 명시하여 지휘관이 검증 가능'],
    ['확률 미제시', '검증되지 않은 예측 확률(예: "가능성 35%")을 제시하지 않고, 기준 대비 상태만 판정'],
  ],
  { boldCols: [0] }
));

body.push(H2('바. 제도화 방안'));
body.push(B('단기(규정 개정 불요, 즉시) : 안전재고 기준표를 부대 자체 보급계획 수립 시 참고자료로 활용, 체크리스트를 보급담당관 일일 업무에 포함', { marker: '(1) ' }));
body.push(B('중기(예규 반영) : 군수 분야 보급 관련 예규에 "도서·격오지 부대 안전재고 기준"을 별표로 신설, 판단절차를 보급 업무 SOP에 편입', { marker: '(2) ' }));
body.push(B('장기(데이터 축적) : 운용 과정에서 보급 시도·성공·회항 사유를 정형 데이터로 축적 → 임계값 실증 보정 → 표본 확보 시 예측모델 도입 검토', { marker: '(3) ' }));
body.push(RP([
  ['※ 즉, '], ['본 제안의 시행 자체가 향후 고도화를 위한 데이터 수집 기반', { bold: true }],
  ['이 된다.'],
], { size: 17, indent: 240 }));

// ─── 4. 기대효과 ────────────────────────────────────────────
body.push(H1('4. 기대효과'));
body.push(H2('가. 효과'));
body.push(dataTable(
  [2200, 7400],
  ['구 분', '내 용'],
  [
    ['전투지속능력', '극단 상황(P95) 대응 재고 확보로 고립 시 임무 수행 능력 유지'],
    ['예산 효율', '위험도 낮은 부대의 과다 재고 해소 — 획일 기준 대비 재고 최적화'],
    ['가용 보급기회 확대', '수단 간 상보성 활용으로, 드론 불가일의 84.7%에서 대체수단 운용 가능'],
    ['판단 품질', '시정 중심 판단으로 전환 시 실제 제약의 95%를 포착 (기존 풍속 중심은 4% 수준)'],
    ['안전', '무리한 보급 강행 방지 — 근거 기반 중단 판단'],
  ],
  { boldCols: [0] }
));

body.push(H2('나. 소요 예산 — 신규 예산 소요 없음'));
body.push(dataTable(
  [2200, 7400],
  ['항 목', '소 요'],
  [
    ['데이터', '기상자료개방포털 — 무료 공개'],
    ['분석 도구', '공개 소스 구현 완료 — 추가 개발 불요'],
    ['시스템', '불요 (체크리스트 방식)'],
    ['교육', '보급담당관 대상 절차 숙지 — 기존 교육에 포함 가능'],
  ],
  { boldCols: [0] }
));

body.push(H2('다. 단계적 적용 로드맵'));
body.push(dataTable(
  [1800, 3200, 4600],
  ['단 계', '시 기', '내 용'],
  [
    ['1단계', '즉시', '백령도 등 1개 부대 시범 적용 — 체크리스트 배포, 판단 결과 기록'],
    ['2단계', '3~6개월', '서해 5도 전 부대 확대 — 부대별 기준표 산출, 실운용 데이터 축적'],
    ['3단계', '1년', '전군 도서·격오지 부대 확대 — 예규 별표 반영, 기준 제도화'],
    ['4단계', '2년~', '축적 데이터 기반 임계값 실증 보정 → 표본 충분 시 예측모델 도입 검토'],
  ],
  { boldCols: [0] }
));
body.push(note(
  '검증 가설 : 1단계 시범 적용의 성패는 "지휘관이 본 체크리스트를 활용해 실제로 보급 시점 결심을 변경하는가"로 ' +
  '판정한다. 기술적 정확도가 아니라 실제 의사결정 변화를 1차 지표로 삼는다.'
));

// ─── 5. 기타 ────────────────────────────────────────────────
body.push(H1('5. 기 타'));
body.push(H2('가. 본 분석의 명시적 한계'));
body.push(B('임계값의 예시성 — 3-나항 임계값은 일반 기준을 참조한 예시값이며 실제 장비 제원이 아니다. 다만 민감도 분석으로 핵심 결론의 강건성은 검증하였다.', { marker: '(1) ' }));
body.push(B('단일 관측지점 — 백령도 1개 지점 분석이다. 관측소와 부대 간 국지풍 차이는 3-다-(7)항 지형 대표성 민감도로 영향 범위를 확인하였으며(풍속 +30% 가정 시에도 최장 고립일수 불변), 드론 주 운용 부대는 현장 풍속 실측이 권장된다.', { marker: '(2) ' }));
body.push(B('최대순간풍속 미반영 — 해당 지점 미제공으로 돌풍 조건을 제외하였다. 드론 판정 정밀도에 영향이 있을 수 있다.', { marker: '(3) ' }));
body.push(B('실제 보급 실적과의 대조 미실시 — 본 분석은 기상 조건상 운용 가능 여부를 판정한 것이며, 실제 보급 성공·실패 이력(Ground Truth)과 대조 검증하지 않았다. 다만 이 괴리의 방향은 특정 가능하다. 기상이 허용해도 정비·인력·행정 사유로 보급이 무산될 수 있는 반면, 기상이 막는데 보급이 성공하는 경우는 드물다. 따라서 본 추정치는 실제 고립 위험의 하한이며, 안전마진 1일이 이를 보정한다. 2단계 운용 시 실적 데이터를 축적하면 직접 검증이 가능하다.', { marker: '(4) ' }));
body.push(note(
  '지형 보정에 관한 입장 : 수치표고모델(DEM)로 관측값을 실제 부대 위치의 풍속으로 정량 보정하는 것은 본 제안의 ' +
  '범위가 아니다. 지형에 의한 국지풍 정량 예측은 별도의 수치모델링 영역이며, 검증 없이 보정값을 제시하는 것은 ' +
  '부정확하다. 지형 정보는 향후 "풍속 증폭 취약 구간" 등 정성적 주의 표시에 한정 활용함이 타당하다.'
));

body.push(H2('나. 향후 과제'));
body.push(dataTable(
  [2600, 7000],
  ['과 제', '내 용'],
  [
    ['임계값 실증화', '실제 운용교범 수치 확보 및 보급 실적 대조'],
    ['관측지점 확대', '전 도서·격오지 부대 인근 지점으로 분석 확대, 부대별 기준표 완성'],
    ['해양 변수 추가', '파고·조위 데이터 결합으로 선박 판정 정밀화'],
    ['시정 관측 확충', '주요 격오지 인근 시정 관측 역량 확보 (정책 과제)'],
    ['데이터 축적 체계', '보급 시도·결과·회항 사유의 정형 수집 체계 설계'],
  ],
  { boldCols: [0] }
));

body.push(H2('다. 재현 가능성'));
body.push(RP([
  ['본 분석의 '], ['전체 코드와 산출 결과는 공개', { bold: true }],
  ['되어 있으며, 누구든 기상자료개방포털에서 데이터를 내려받아 동일 결과를 재현할 수 있다. ' +
   '파이프라인은 데이터 로더, 1~3단계 분석 모듈, 민감도 분석, 시각화(5종)로 구성된다.'],
]));
body.push(img('02_annual_isolation_trend.png', 470, 209));
body.push(caption('[그림 6] 연도별 최장 연속 고립일수 추이 및 권고 안전재고 기준선 — 2019년 이후의 평온기는 위험 소멸이 아닌 사건 집중 패턴상의 휴지기'));

body.push(new Paragraph({
  spacing: { before: 200, after: 0 },
  border: { top: { style: BorderStyle.SINGLE, size: 8, color: NAVY, space: 6 } },
  children: [new TextRun({
    text: '도서·격오지 보급을 막는 것은 강풍이 아니라 안개였다. 이 결론은 10년의 관측 기록에서 일관되며, ' +
          '임계값을 어떻게 조정해도 바뀌지 않는다. 최근 수년간 고립이 없었던 것은 이 문제가 해소되었다는 ' +
          '뜻이 아니라, 사건이 몰아서 발생하는 패턴상 지금이 평온기라는 뜻이다. 다음 몰림이 오기 전, ' +
          '평온한 지금이 기준을 정비할 적기이다.',
    font: FONT, size: 18, bold: true, color: NAVY,
  })],
}));

// ═══════════════════════════════════════════════════════════
const doc = new Document({
  styles: { default: { document: { run: { font: FONT, size: 19 } } } },
  sections: [{
    properties: {
      page: {
        size: { width: 11906, height: 16838 },
        margin: { top: 1000, right: 1100, bottom: 1000, left: 1100 },
      },
    },
    footers: {
      default: new Footer({ children: [new Paragraph({
        alignment: AlignmentType.CENTER,
        children: [new TextRun({ children: [PageNumber.CURRENT, ' / ', PageNumber.TOTAL_PAGES],
                                font: FONT, size: 15, color: '999999' })],
      })]}),
    },
    children: body,
  }],
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync('/mnt/user-data/outputs/보급윈도우_제안서(공모서식).docx', buf);
  console.log('created');
});
