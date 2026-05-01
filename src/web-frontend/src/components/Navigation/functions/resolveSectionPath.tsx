import type { Section } from "../../../pages/predictions/PredictionsHub";
import type { HubContext } from "../../../pages/predictions/PredictionsHub";
import { PREDICTION_LEAGUE_OPTIONS } from "../../../utils/footballSeason";

const DEFAULT_CONTEXT: HubContext = {
  fixture: null,
  teamExamples: [],
  trustLeague: PREDICTION_LEAGUE_OPTIONS[0].value,
};

export const resolveSectionPath = (
  section: Section,
  context: HubContext = DEFAULT_CONTEXT,
): string =>
    section.getPath
      ? section.getPath(context)
      : (section.path ?? "/predictions/hub");
