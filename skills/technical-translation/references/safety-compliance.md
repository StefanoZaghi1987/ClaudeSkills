# Safety & Compliance Language Reference

Standard translations for safety warnings, regulatory terminology, and compliance language in technical documentation.

## Safety Signal Words

### Critical Hierarchy

**Italian → English**

1. **PERICOLO** → **DANGER**
   - Highest severity level
   - Indicates immediate hazard resulting in death or serious injury
   - Red color typically used
   - Example: "PERICOLO: Tensione elettrica pericolosa"
   - Translation: "DANGER: Hazardous electrical voltage"

2. **AVVERTENZA** / **AVVERTIMENTO** → **WARNING**
   - Serious hazard that could result in death or serious injury
   - Orange color typically used
   - Example: "AVVERTENZA: Superfici calde"
   - Translation: "WARNING: Hot surfaces"

3. **ATTENZIONE** / **CAUTELA** → **CAUTION**
   - Hazard that could result in minor or moderate injury
   - Yellow color typically used
   - Example: "ATTENZIONE: Rischio di schiacciamento"
   - Translation: "CAUTION: Risk of crushing"

4. **NOTA** → **NOTICE**
   - Important information not related to personal injury
   - Blue color typically used
   - Example: "NOTA: Consultare il manuale"
   - Translation: "NOTICE: Refer to manual"

**AVVISO** is not one of the four standard signal words; the Phase 5 severity rules place it, exactly as they place the `ATTENZIONE` trap case.

### Other Target Languages

| Level | German | French | Spanish | Portuguese |
| --- | --- | --- | --- | --- |
| DANGER | GEFAHR | DANGER | PELIGRO | PERIGO |
| WARNING | WARNUNG | AVERTISSEMENT | ADVERTENCIA | AVISO |
| CAUTION | VORSICHT | ATTENTION | PRECAUCIÓN | ATENÇÃO |
| NOTICE | HINWEIS | AVIS | NOTA | NOTA |

Italian `ATTENZIONE` sits at CAUTION level and becomes Spanish `PRECAUCIÓN` — `ATENCIÓN` is a generic Spanish word outside the graded signal-word set, while Portuguese `ATENÇÃO` is the graded CAUTION word (`CUIDADO` is an accepted variant at the same level). French `AVIS` and German `HINWEIS` follow ANSI Z535.4 Annex D, the standard's own multilingual signal-word table; Portuguese `PERIGO`, `AVISO` and `ATENÇÃO` follow ISO 3864-2 Annex B; Spanish and Portuguese `NOTA` follow notice-level practice in those languages' machinery manuals.

## Safety Warning Components

### Standard Structure

```
[SIGNAL WORD]
[Hazard identification]
[Consequences of not following warning]
[How to avoid the hazard]
```

### Common Phrases

**Hazard Identification:**
- rischio di morte → risk of death / fatal hazard
- rischio di lesioni gravi → risk of serious injury
- rischio di scosse elettriche → risk of electric shock
- rischio di ustioni → risk of burns
- rischio di schiacciamento → risk of crushing
- rischio di taglio → risk of cutting
- rischio di intrappolamento → risk of entrapment
- pericolo di esplosione → explosion hazard
- pericolo di incendio → fire hazard
- materiale tossico → toxic material
- radiazioni pericolose → hazardous radiation

**Consequences:**
- può causare la morte → may cause death / can be fatal
- può causare lesioni gravi → may cause serious injury
- può provocare ustioni → may cause burns
- può danneggiare l'apparecchiatura → may damage the equipment
- può causare malfunzionamenti → may cause malfunctions

**Preventive Actions:**
- non rimuovere i ripari → do not remove guards
- indossare dispositivi di protezione → wear protective equipment
- scollegare l'alimentazione → disconnect power supply
- attendere l'arresto completo → wait for complete stop
- seguire le procedure di lockout/tagout → follow lockout/tagout procedures
- mantenere le mani a distanza → keep hands clear
- utilizzare solo personale qualificato → use qualified personnel only

## Personal Protective Equipment (PPE)

- dispositivi di protezione individuale (DPI) → personal protective equipment (PPE)
- occhiali di protezione → safety glasses / protective eyewear
- guanti di protezione → protective gloves
- scarpe antinfortunistiche → safety shoes / safety footwear
- casco → hard hat / safety helmet
- protezioni auricolari → hearing protection
- maschera respiratoria → respiratory protection / respirator
- tuta di protezione → protective suit / coveralls
- visiera → face shield

## Regulatory References

### European Standards

**General:**
- Direttiva Macchine → Machinery Directive
- Marcatura CE → CE Marking
- Dichiarazione di Conformità → Declaration of Conformity
- Valutazione del Rischio → Risk Assessment
- Manuale d'Uso e Manutenzione → Operating and Maintenance Manual

**Specific Standards:**
- EN ISO 12100 → Safety of machinery - General principles for design - Risk assessment and risk reduction
- EN 60204-1 → Safety of machinery - Electrical equipment of machines
- EN ISO 13849-1 → Safety of machinery - Safety-related parts of control systems
- EN ISO 13857 → Safety of machinery - Safety distances
- EN 61508 → Functional safety of electrical/electronic/programmable electronic safety-related systems
- EN 62061 → Safety of machinery - Functional safety of safety-related control systems

### International Standards

- ISO 9001 → Quality Management Systems
- ISO 14001 → Environmental Management Systems
- ISO 45001 → Occupational Health and Safety Management Systems
- IEC 60529 → Degrees of protection provided by enclosures (IP Code)
- IEC 61000 → Electromagnetic compatibility (EMC)

### North American Standards

- ANSI → American National Standards Institute
- NFPA → National Fire Protection Association
- OSHA → Occupational Safety and Health Administration
- UL → Underwriters Laboratories
- CSA → Canadian Standards Association

## Compliance Terminology

### Certification & Approval
- conforme a → complies with / conforms to / in accordance with
- certificato → certified
- approvato → approved
- omologato → type-approved / homologated
- collaudato → tested / inspected
- verificato → verified
- validato → validated

### Documentation
- documentazione tecnica → technical documentation
- fascicolo tecnico → technical file
- istruzioni per l'uso → operating instructions
- manuale di installazione → installation manual
- dichiarazione di incorporazione → declaration of incorporation
- certificato di conformità → certificate of conformity

### Responsibility
- fabbricante → manufacturer
- costruttore → builder / manufacturer
- distributore → distributor
- installatore → installer
- utilizzatore → user
- datore di lavoro → employer
- personale qualificato → qualified personnel
- personale autorizzato → authorized personnel
- persona competente → competent person

## Safety Procedures

### Lockout/Tagout (LOTO)
- procedura di lockout → lockout procedure
- blocco dell'energia → energy isolation
- dissipazione dell'energia residua → dissipation of residual energy
- cartellino di sicurezza → safety tag
- lucchetto di sicurezza → safety padlock
- verifica dell'isolamento → isolation verification

### Emergency Procedures
- procedura di emergenza → emergency procedure
- arresto di emergenza → emergency stop
- evacuazione → evacuation
- piano di emergenza → emergency plan
- uscita di emergenza → emergency exit
- punto di raccolta → assembly point
- primo soccorso → first aid

### Maintenance Safety
- manutenzione programmata → scheduled maintenance
- manutenzione straordinaria → unscheduled maintenance / extraordinary maintenance
- fermo macchina → machine shutdown
- messa fuori servizio → taking out of service
- rimessa in servizio → return to service
- ispezione → inspection
- controllo periodico → periodic check

## Environmental & Disposal

- smaltimento → disposal
- riciclaggio → recycling
- rifiuti → waste
- rifiuti pericolosi → hazardous waste
- raccolta differenziata → separate collection / sorted waste
- RAEE (Rifiuti di Apparecchiature Elettriche ed Elettroniche) → WEEE (Waste Electrical and Electronic Equipment)
- sostanze pericolose → hazardous substances
- RoHS (Restriction of Hazardous Substances) → RoHS
- REACH → REACH (Registration, Evaluation, Authorization and Restriction of Chemicals)

## Quality & Performance

- requisiti essenziali di sicurezza → essential safety requirements
- livello di prestazione → performance level
- categoria di sicurezza → safety category
- tempo di risposta → response time
- affidabilità → reliability
- disponibilità → availability
- manutenibilità → maintainability
- ciclo di vita → life cycle / service life

## Critical Translation Notes

1. **Be Specific**: Translate hazards precisely - "risk of electric shock" not just "electrical hazard"
2. **Standard References**: Keep standard numbers exactly as written (EN 60204-1, not "EN sixty thousand two hundred four dash one")
3. **Legal Terminology**: For regulatory terms, use established legal translations
4. **Consistency**: Use identical translations for safety terms throughout entire document
5. **Cultural Adaptation**: Consider target market regulations (EU vs. US standards) while maintaining safety integrity

## Verification Checklist

The safety expansion of the Phase 6 Safety check, run whenever this file was used:

- ✓ Hazard descriptions clear and specific?
- ✓ Consequences explicitly stated?
- ✓ Preventive actions clearly described?
- ✓ PPE requirements accurately translated?
- ✓ Emergency procedures clear and actionable?
