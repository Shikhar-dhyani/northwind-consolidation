"""One orchestrator; no network, model, or nondeterministic accounting step."""

from decimal import localcontext
from pathlib import Path

from .accounting import (block_uk_acquisition, eliminate_india, eliminate_intercompany,
                         prior_equity, record_transit, retranslate_uk, translate)
from .fx import FxBook
from .inputs import Inputs
from .journals import apply_journals
from .model import Audit, EPSILON, InputError, total
from .periods import cut_india
from .reporting import build_reports, emit, emit_failure
from .scenarios import alternative
from .publication import check_destination, execute


def run(data: Path, out: Path):
    requested_out = Path(out)
    data, out = Path(data).resolve(), Path(out).resolve()
    if out == data or data in out.parents or out in data.parents:
        raise InputError('Input and output directories must be separate, non-nested paths')
    check_destination(requested_out)
    audit = Audit()
    return execute(data, out, audit, _calculate, emit_failure)


def _calculate(data, out, audit):
        with localcontext() as context:
            context.prec = 40
            inputs = Inputs(data, audit)
            local = inputs.load()
            fx = FxBook(inputs)
            counts, journals = apply_journals(inputs, local)
            bank = retranslate_uk(inputs, fx, local)
            causes, ic_refs = record_transit(inputs, fx, local)
            local, pre_profit = cut_india(inputs, local)
            opening = prior_equity(inputs)
            translated, india_oci = translate(inputs, fx, local, opening)
            eliminations = eliminate_intercompany(inputs, translated, causes)
            india, india_entries = eliminate_india(inputs, fx, local, translated, pre_profit, india_oci)
            eliminations.extend(india_entries)
            eliminations.extend(block_uk_acquisition(inputs, translated))
            for code in ('1250', '2150', '4200', '6300', '1610'):
                value = total(translated, account=code)
                audit.check(f'{code} eliminated in full', abs(value['value']) < EPSILON, value['sources'])
            audit.check('NCI account matches closing control',
                abs(-total(translated, account='3400')['value'] - india['nci_closing']) < EPSILON,
                india['sources'])
            reports, accounts = build_reports(inputs, translated, opening, india, bank, counts, causes, ic_refs)
            reports['scenarios/alternative_disclosed_assumptions.json'] = alternative(
                inputs, fx, opening, local, translated, india, bank, reports)
            emit(out, inputs, reports, accounts, translated, eliminations, journals)
            return reports['control_figures_sd.json']
