# Rent Sloth audit

## 01-zelle-lopez

- **kind**: money_received `ok`
- **payer**: Maria Lopez `ok`
- **amount**: 1350.0 `ok`
- **date**: 2026-10-31 `ok`
- **memo**: Nov rent 1A `ok`
- **reference**: ZL8842QX1 `ok`

## 02-venmo-kayla

- **kind**: money_received `ok`
- **payer**: Kayla Price `ok`
- **amount**: 750.0 `ok`
- **date**: 2026-11-01 `ok`
- **memo**: rent nov half 🏠 `ok`
- **reference**: 4271930055812 `ok`

## 03-venmo-devon

- **kind**: money_received `ok`
- **payer**: Devon Price `FIXED` model said 'Venmo <venmo@venmo.example>'
- **amount**: 750.0 `ok`
- **date**: 2026-11-01 `ok`
- **memo**: other half `ok`
- **reference**: 4271932210467 `ok`

## 04-cashapp-okafor

- **kind**: money_received `ok`
- **payer**: Samuel Okafor `ok`
- **amount**: 1200.0 `ok`
- **date**: 2026-11-02 `ok`
- **memo**: Apt 2A November `ok`
- **reference**: #D5RT7KQ `ok`

## 05-ach-nair

- **kind**: money_received `ok`
- **payer**:  `CHECK` no payer named (model said 'First Prairie Bank')
- **amount**: 650.0 `ok`
- **date**: 2026-11-03 `ok`
- **memo**: ACH CREDIT PRIYA NAIR RENT PMT `ok`
- **reference**: 091000019283746 `ok`

## 06-zelle-romero

- **kind**: money_received `ok`
- **payer**: Ana Romero `ok`
- **amount**: 1650.0 `ok`
- **date**: 2026-11-01 `FIXED` used the message's Date header
- **memo**:  `ok`
- **reference**: ZL8851MB4 `ok`

## 07-venmo-request-becker

- **kind**: payment_request `ok`
- **payer**:  `n/a` not money received
- **amount**: 1400.0 `ok`
- **date**: 2026-11-02 `ok`
- **memo**: Nov rent 3B `ok`
- **reference**:  `ok`

## 08-promo

- **kind**: not_a_payment `ok`
- **payer**:  `n/a` not money received
- **amount**: 500.0 `ok`
- **date**: 2026-11-02 `ok`
- **memo**: Get $50 when you open a High-Yield Savings account
Open a High-Yield Savings account by November 30, 2026 and deposit $500 to get a $50 bonus.
Terms apply. This is an advertisement. `ok`
- **reference**:  `ok`

## 09-zelle-lopez-again

- **kind**: money_received `ok`
- **payer**: Maria Lopez `ok`
- **amount**: 1350.0 `ok`
- **date**: 2026-10-31 `ok`
- **memo**: Nov rent 1A `ok`
- **reference**: ZL8842QX1 `ok`

## 10-refund-romero

- **kind**: money_sent `FIXED` model said money_received; the wording says money_sent
- **payer**:  `n/a` not money received
- **amount**: 200.0 `ok`
- **date**: 2026-11-02 `FIXED` used the message's Date header
- **memo**: deposit refund - pet deposit `ok`
- **reference**: ZL8860TT2 `ok`

## 11-mobile-check

- **kind**: money_received `ok`
- **payer**:  `CHECK` no payer named (model said 'First Prairie Bank')
- **amount**: 300.0 `ok`
- **date**: 2026-11-04 `ok`
- **memo**:  `ok`
- **reference**: 1042 `ok`

## 12-zelle-rivera

- **kind**: money_received `ok`
- **payer**: J Rivera `ok`
- **amount**: 85.0 `ok`
- **date**: 2026-11-03 `ok`
- **memo**: laundry card `ok`
- **reference**: ZL8873AA9 `ok`

## 13-venmo-becker-october

- **kind**: money_received `ok`
- **payer**: Tom Becker `ok`
- **amount**: 1400.0 `ok`
- **date**: 2026-10-02 `ok`
- **memo**: oct rent `ok`
- **reference**: 4198820017733 `ok`

## Units

- 1A Maria Lopez: $1,350.00 of $1,350.00, Paid
- 1B Devon Price & Kayla Price: $1,500.00 of $1,500.00, Paid
- 2A Sam Okafor: $1,200.00 of $1,200.00, Paid
- 2B Priya Nair: $650.00 of $1,300.00, Partial ($650.00 short)
- 3A Luis Romero & Ana Romero: $1,650.00 of $1,650.00, Paid
- 3B Tom Becker: $0.00 of $1,400.00, Not yet

## Not counted

- 07-venmo-request-becker: payment_request
- 08-promo: not_a_payment
- 09-zelle-lopez-again: duplicate of 01-zelle-lopez
- 10-refund-romero: money_sent
- 13-venmo-becker-october: dated 2026-10-02, outside Nov 2026
