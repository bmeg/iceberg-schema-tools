import React from "react";
import "./styles.css";
import Cytoscape from "cytoscape";
import Dagre from "cytoscape-dagre"
import CytoscapeComponent from "react-cytoscapejs";

Cytoscape.use(Dagre);
const dataPaths = [
  // this is where the datapath is defined
  // ex: public/data/graph.json
  { file: "graph", adapter: "gen3"}
];

const processData = (data, selectedNodes) => {
  const eles = []; //categories.map((c) => ({ data: { id: c, label: c } }));
  const edges = [];
  console.log("Processing:", data, selectedNodes);
  Object.entries(data).forEach((key,index) => {
    //console.log("key[1] ",key[1].data)
    if ("id" in key[1].data === true){
      eles.push(key[1]);
    }
    else if ("source" in key[1].data === true && "target" in key[1].data === true){
      edges.push({"data":{"source":key[1].data.source,"target":key[1].data.target}});
    }

});
  console.log("Elements:", eles);
  console.log("Edges:", edges);
  return { elements: [...eles, ...edges] };
};

const formatPath = (p) => `/data/${p}.json`;
export default function App() {
  const [dataPath, setDataPath] = React.useState(dataPaths[0].file);
  const [nodes, setNodes] = React.useState([]);
  const [selected, setSelected] = React.useState("[Select A Node]");
  const [properties, setProperties] = React.useState("");
  const [temp, setTemp] = React.useState(0);
  const [OldData, setData] = React.useState();
  const cy = React.useRef();

  React.useEffect(() => {
    if (cy.current) {
      cy.current.on('tap', 'node', function(e){
        setSelected(this.id());
        const props = this.data()["properties"].map((x) => {
          return (<li>{x}</li>)
        })
        setProperties(props);
        e.target.addClass('highlighted').outgoers().addClass('highlighted');
        e.target.addClass('highlighted').incomers().addClass('highlighted');
      });

      cy.current.on("click", function(evt){
        cy.current.edges().removeClass("highlighted")
      })
      cy.current
        .layout({
          name: "dagre",//"cose-bilkent",
          spacingFactor: 1.3
        })
        .run();

      window.cy = cy.current;
      
    }
  }, [nodes, cy]);
  
  // fetch data from the datapath every 2 seconds.
  React.useEffect(()=>{
    setInterval(()=>{
      setTemp((prevTemp)=>prevTemp+1)
    }, 2000)
  }, [])

  React.useEffect(() => {
    console.log("Loading: ", formatPath(dataPath));
    const path = dataPaths.find((v) => v.file === dataPath);
    fetch(formatPath(path.file))
      .then((r) => r.json())
      .then((data) => {
        switch (path.adapter) {
          case "gen3":
            const { elements } = processData(data, []);
            // if the actual data coming from the fetch changes, then set the state hooks with the new data
            if (JSON.stringify(data) !== JSON.stringify(OldData)){
              setNodes(elements);
              setData(data);
            }   
            break;
          default:
            break;
        }
      });
  }, [dataPath, temp, OldData]);

  return (
    <div className="App" style={{ width: "100%", height: "100vh" }}>
      <select
        value={dataPath}
        onChange={(e) => setDataPath(e.currentTarget.value)}
      >
        {dataPaths.map((p) => (
          <option value={p.file} key={p.file}>
            {p.file} - {p.adapter}
          </option>
        ))}
      </select>
      <div className="parent">
      <span>Properties For: {selected} <ul>{properties}</ul> </span>
      <CytoscapeComponent
        cy={(ref) => {
          cy.current = ref;
          cy.current.resize()
        }}
    
        elements={nodes}
        style={{
          width: "100%",
          height: "100vh"
        }}
        stylesheet={[
          {
            selector: "node",
            style: {
              label: "data(id)",
              "font-size": "40px",
              "background-color": "black"
            }
          }, 
          {
            selector: "node:selected",
            style: {
              "background-color": "#FF9466",
              "overlay-color": "blue",
            },
          },
          {
            selector: "edge",
            style: {
              "line-color": "lightgreen",
              "width": 4.5
            }
          },  
          {
            selector: "edge.highlighted",
            style: { 
              "line-color": "#ff00ff", 
              "target-arrow-color": "#b830f7"
            }
          },
        ]}
      />
      </div>
      </div>
  );
}
