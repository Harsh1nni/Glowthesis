// Glowthesis demo front end
// Stores a "result" in localStorage and shows it on results.html

(function () {
  const byId = (id) => document.getElementById(id);

  const analyseForm = byId("analyseForm");
  const fillExampleBtn = byId("fillExample");

  // Analyse page behaviour
  if (analyseForm) {
    analyseForm.addEventListener("submit", (e) => {
      e.preventDefault();

      const inputText = byId("inputText").value.trim();
      const mode = byId("mode").value;
      const detail = byId("detail").value;

      if (!inputText) {
        alert("Please paste some text to analyse.");
        return;
      }

      
      const wordCount = inputText.split(/\s+/).filter(Boolean).length;
      const charCount = inputText.length;

      const output = [
        `Mode: ${mode}`,
        `Detail: ${detail}`,
        "",
        `Word count: ${wordCount}`,
        `Character count: ${charCount}`,
        "",
        "Next step: replace this demo output with your real Flask backend results."
      ].join("\n");

      const payload = {
        createdAt: new Date().toISOString(),
        input: inputText,
        output
      };

      localStorage.setItem("glowthesis_latest_result", JSON.stringify(payload));

      // Go to results page
      window.location.href = "/results";
    });

    if (fillExampleBtn) {
      fillExampleBtn.addEventListener("click", () => {
        byId("inputText").value =
          "Glowthesis is a project demonstrating a clean Flask front end.\n\n" +
          "Paste any text here and click Run analysis to see demo results.\n" +
          "Later, this will be replaced by real backend processing.";
      });
    }
  }

  // Results page 
  const resultsMeta = byId("resultsMeta");
  const resultsEmpty = byId("resultsEmpty");
  const resultsContent = byId("resultsContent");
  const resultInput = byId("resultInput");
  const resultOutput = byId("resultOutput");
  const clearResults = byId("clearResults");

  if (resultsMeta && resultsEmpty && resultsContent && resultInput && resultOutput) {
    const raw = localStorage.getItem("glowthesis_latest_result");
    if (!raw) {
      resultsMeta.textContent = "No run saved yet.";
      resultsEmpty.hidden = false;
      resultsContent.hidden = true;
    } else {
      const data = JSON.parse(raw);
      const when = new Date(data.createdAt);

      resultsMeta.textContent = `Saved: ${when.toLocaleString()}`;
      resultInput.textContent = data.input;
      resultOutput.textContent = data.output;

      resultsEmpty.hidden = true;
      resultsContent.hidden = false;
    }
  }

  if (clearResults) {
    clearResults.addEventListener("click", () => {
      localStorage.removeItem("glowthesis_latest_result");
      window.location.reload();
    });
  }
})();
