#include <string>

#include <EveryBeam/load.h>

#include <casacore/ms/MeasurementSets/MeasurementSet.h>
#include <casacore/ms/MeasurementSets/MSObsColumns.h>
#include <casacore/tables/Tables/SetupNewTab.h>

int main() {
  // Create a MeasurementSet with an invalid telescope name.
  casacore::TableDesc table_desc = casacore::MS::requiredTableDesc();
  casacore::SetupNewTable new_table("table", table_desc, casacore::Table::New);
  casacore::MeasurementSet ms(new_table);
  ms.createDefaultSubtables(casacore::Table::New);
  casacore::MSObservation& obs = ms.observation();
  casacore::MSObservationColumns obs_col(obs);
  obs.addRow();
  obs_col.telescopeName().put(0, "INVALID_NAME");
  obs.flush();

  // Attempt to load the MeasurementSet and expect an error.
  bool caught_error = false;
  try {
    const everybeam::Options options;
    everybeam::Load(ms, options);
  } catch (const std::runtime_error& e) {
    if (std::string(e.what()).find(
      "telescope type INVALID_NAME is not implemented") != std::string::npos) {
      caught_error = true;
    }
  }

  // If the error was caught as expected, return success.
  // Otherwise, return failure.
  return caught_error ? 0 : 1;
}
