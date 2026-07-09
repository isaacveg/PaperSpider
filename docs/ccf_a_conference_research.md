# CCF A Conference Implementation Research

Source baseline: CCF seventh edition directory, released 2026-03-31 and corrected 2026-04-09.

Primary sources:

- CCF official categorized directory: <https://www.ccf.org.cn/Academic_Evaluation/By_category/>
- Secondary proceedings/source hint: <https://github.com/ccfddl/ccf-deadlines>

Legend:

- `done`: already available in PaperSpider before this pass.
- `later`: researched, but better left for a publisher-specific or DBLP metadata-only layer.
- Difficulty: `low`, `medium`, `high`.

## Summary

The current `ConferenceBase` model fits conferences well: `list_papers(year)`,
`fetch_details`, `fetch_pdf`, and `fetch_bibtex`. It does not fit journals without
adding journal volume/issue concepts.

Implemented in this pass:

- CVF Open Access: ICCV.
- USENIX: FAST and USENIX Security.
- Venue-owned proceedings: AAAI, IJCAI, NDSS, VLDB.

Validated in this pass:

- Unit test suite: `.venv/bin/python -m unittest discover -s tests -v`
- Whitespace check: `git diff --check`
- Live smoke samples for AAAI, ICCV, IJCAI, FAST, USENIX Security, NDSS, and VLDB.

The large remaining surface is ACM/IEEE/Springer-heavy. Those venues are possible,
but the right implementation is a shared DBLP/DOI/Crossref fallback plus optional
publisher-specific enhancement, not one-off scrapers per venue.

## CCF A Conferences

| Domain | Venue | Status | Source direction | Difficulty | Notes |
|---|---:|---|---|---|---|
| Architecture/Parallel/Storage | PPoPP | later | ACM/DOI/DBLP | medium | Needs shared ACM/DBLP layer. |
| Architecture/Parallel/Storage | FAST | done | USENIX | low | Same family as NSDI/OSDI/ATC. |
| Architecture/Parallel/Storage | DAC | later | ACM/IEEE/DBLP | medium | Proceedings source changes over years. |
| Architecture/Parallel/Storage | HPCA | later | IEEE/DBLP | high | IEEE-heavy; metadata-only first. |
| Architecture/Parallel/Storage | MICRO | later | ACM/IEEE/DBLP | medium | Good ACM/DBLP candidate. |
| Architecture/Parallel/Storage | SC | later | IEEE/ACM/DBLP | high | Large proceedings; source varies. |
| Architecture/Parallel/Storage | ASPLOS | later | ACM/DBLP | medium | Good shared ACM candidate. |
| Architecture/Parallel/Storage | ISCA | later | ACM/IEEE/DBLP | medium | Good shared ACM/DBLP candidate. |
| Architecture/Parallel/Storage | USENIX ATC | done | USENIX | low | Existing implementation. |
| Architecture/Parallel/Storage | EuroSys | later | ACM/DBLP | medium | Good shared ACM candidate. |
| Computer Networks | SIGCOMM | done | SIGCOMM site/Crossref | medium | Existing implementation. |
| Computer Networks | MobiCom | later | ACM/DBLP | medium | Good shared ACM candidate. |
| Computer Networks | INFOCOM | later | IEEE/DBLP | high | Metadata-only first. |
| Computer Networks | NSDI | done | USENIX | low | Existing implementation. |
| Network/Information Security | CCS | later | ACM/DBLP | medium | Good shared ACM candidate. |
| Network/Information Security | EUROCRYPT | later | IACR/Springer/DBLP | medium | Needs IACR/LNCS handling. |
| Network/Information Security | S&P | later | IEEE/DBLP | high | Metadata-only first. |
| Network/Information Security | CRYPTO | later | IACR/Springer/DBLP | medium | Needs IACR/LNCS handling. |
| Network/Information Security | USENIX Security | done | USENIX | low | Same family as NSDI/OSDI/ATC. |
| Network/Information Security | NDSS | done | NDSS proceedings | low | Venue-owned pages expose paper PDFs; BibTeX is synthesized. |
| Software/System/PL | PLDI | later | ACM/DBLP | medium | Good shared ACM candidate. |
| Software/System/PL | POPL | later | ACM/DBLP | medium | Good shared ACM candidate. |
| Software/System/PL | FSE | later | ACM/DBLP | medium | Good shared ACM candidate. |
| Software/System/PL | SOSP | later | ACM/DBLP | medium | Good shared ACM candidate. |
| Software/System/PL | OOPSLA | later | ACM/PACMPL/DBLP | medium | Needs PACMPL/OOPSLA nuance. |
| Software/System/PL | ASE | later | ACM/IEEE/DBLP | medium | Good DBLP candidate. |
| Software/System/PL | ICSE | later | ACM/IEEE/DBLP | medium | Good DBLP candidate. |
| Software/System/PL | ISSTA | later | ACM/DBLP | medium | Good shared ACM candidate. |
| Software/System/PL | OSDI | done | USENIX | low | Existing implementation. |
| Software/System/PL | FM | later | Springer/DBLP | high | Metadata-only first. |
| Database/Data Mining/IR | SIGMOD | later | ACM/DBLP | medium | Good shared ACM candidate. |
| Database/Data Mining/IR | SIGKDD | later | ACM/DBLP | medium | Good shared ACM candidate. |
| Database/Data Mining/IR | ICDE | later | IEEE/DBLP | high | Metadata-only first. |
| Database/Data Mining/IR | SIGIR | later | ACM/DBLP | medium | Good shared ACM candidate. |
| Database/Data Mining/IR | VLDB | done | PVLDB/VLDB site | low | Venue-owned source is suitable; BibTeX is synthesized. |
| Theory | STOC | later | ACM/DBLP | medium | Good shared ACM/DBLP candidate. |
| Theory | SODA | later | SIAM/DBLP | high | Metadata-only first. |
| Theory | CAV | later | Springer/DBLP | high | Metadata-only first. |
| Theory | FOCS | later | IEEE/DBLP | high | Metadata-only first. |
| Theory | LICS | later | ACM/IEEE/DBLP | high | Metadata-only first. |
| Graphics/Multimedia | ACM MM | later | ACM/DBLP | medium | Good shared ACM candidate. |
| Graphics/Multimedia | SIGGRAPH | later | ACM/TOG/DBLP | medium | Needs proceedings/TOG handling. |
| Graphics/Multimedia | VR | later | IEEE/DBLP | high | Metadata-only first. |
| Graphics/Multimedia | IEEE VIS | later | IEEE/TVCG/DBLP | high | Metadata-only first. |
| AI | AAAI | done | AAAI proceedings | low | Venue-owned open proceedings. |
| AI | NeurIPS | done | NeurIPS/OpenReview/PMLR | low | Existing implementation. |
| AI | ACL | done | ACL Anthology | low | Existing implementation. |
| AI | CVPR | done | CVF Open Access | low | Existing implementation. |
| AI | ICCV | done | CVF Open Access | low | Same family as CVPR. |
| AI | ICML | done | PMLR/OpenReview | low | Existing implementation. |
| AI | IJCAI | done | IJCAI proceedings | low | Venue-owned pages expose PDFs and BibTeX. |
| HCI/Ubiquitous | CSCW | later | ACM/DBLP | medium | Good shared ACM candidate. |
| HCI/Ubiquitous | CHI | later | ACM/DBLP | medium | Good shared ACM candidate. |
| HCI/Ubiquitous | UbiComp/IMWUT | later | ACM/IMWUT/DBLP | medium | Needs conference/journal hybrid handling. |
| HCI/Ubiquitous | UIST | later | ACM/DBLP | medium | Good shared ACM candidate. |
| Cross/Comprehensive/Emerging | WWW | later | ACM/DBLP | medium | Good shared ACM candidate. |
| Cross/Comprehensive/Emerging | RTSS | later | IEEE/DBLP | high | Metadata-only first. |
| Cross/Comprehensive/Emerging | WINE | later | Springer/DBLP | high | Metadata-only first. |
