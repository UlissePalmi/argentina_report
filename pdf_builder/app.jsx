/* global React, ReactDOM, DesignCanvas, DCSection, DCArtboard, VariationA, VariationB, VariationC */

function App() {
  return (
    <DesignCanvas
      title="Macro Research — Layout Explorations"
      subtitle="3 directions · Classic Wall Street paper · pipeline-ready slots"
    >
      <DCSection id="layouts" title="Document Layouts" subtitle="Drag to reorder · click any artboard to focus">
        <DCArtboard id="var-a" label="A · Classic Note · masthead + dense grid" width={880} height={1380}>
          <VariationA />
        </DCArtboard>
        <DCArtboard id="var-b" label="B · Left-Rail · persistent TOC & levels" width={880} height={1380}>
          <VariationB />
        </DCArtboard>
        <DCArtboard id="var-c" label="C · Editorial · single column with marginalia" width={880} height={1380}>
          <VariationC />
        </DCArtboard>
      </DCSection>
    </DesignCanvas>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
