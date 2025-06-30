import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import './App.css';
import data from './data.json';

const App = () => {
  const svgRef = useRef();
  const tooltipRef = useRef();
  const [filterLevel, setFilterLevel] = useState('minimalCore');
  const [layoutType, setLayoutType] = useState('force');
  const [customLayers, setCustomLayers] = useState({
    layer2: 'ResearchSubject',
    layer3: 'Patient,Specimen,DocumentReference,MedicationAdministration,Observation',
    layer4: ''
  });

  const handleFilterChange = (newFilter) => {
    setFilterLevel(newFilter);
    if (newFilter === 'full') {
      setLayoutType('force');
    }
  };

  const filterLevels = {
    full: {
      name: 'Full Graph',
      description: 'All entities and relationships from schema',
      dataKey: 'full'
    },
    minimalCore: {
      name: 'Minimal Core',
      description: 'FHIR R5 essential entities only',
      dataKey: 'minimal'
    }
  };

  const getFilteredData = () => {
    const level = filterLevels[filterLevel];
    return data[level.dataKey];
  };

  useEffect(() => {
    const filteredData = getFilteredData();
    const svg = d3.select(svgRef.current);
    const tooltip = d3.select(tooltipRef.current);

    svg.selectAll("*").remove();
    
    const width = 1200;
    const height = 800;
    
    svg.attr('width', width).attr('height', height);
    
    let simulation, treeLayout, root;
    
    if (layoutType === 'tree' && filterLevel === 'minimalCore') {
      treeLayout = d3.tree().size([height - 100, width - 300]);

      const rootNodeId = filteredData.nodes.find(n => n.id === 'ResearchStudy')?.id || filteredData.nodes[0]?.id;
      
      const getConnectionLevels = () => {
        const levels = { [rootNodeId]: 0 };
        const visited = new Set([rootNodeId]);

        const layer2Entities = customLayers.layer2.split(',').map(s => s.trim()).filter(s => s);
        const layer3Entities = customLayers.layer3.split(',').map(s => s.trim()).filter(s => s);
        const layer4Entities = customLayers.layer4.split(',').map(s => s.trim()).filter(s => s);

        const directlyConnected = filteredData.links
          .filter(l => {
            const sourceId = l.source?.id || l.source;
            const targetId = l.target?.id || l.target;
            return sourceId === rootNodeId || targetId === rootNodeId;
          })
          .map(l => {
            const sourceId = l.source?.id || l.source;
            const targetId = l.target?.id || l.target;
            return sourceId === rootNodeId ? targetId : sourceId;
          })
          .filter(id => id !== rootNodeId);
        
        if (layer2Entities.length > 0) {
          layer2Entities.forEach(entityId => {
            if (filteredData.nodes.find(n => n.id === entityId)) {
              levels[entityId] = 1;
              visited.add(entityId);
            }
          });
        } else {
          directlyConnected.forEach(entityId => {
            levels[entityId] = 1;
            visited.add(entityId);
          });
        }
        layer3Entities.forEach(entityId => {
          if (filteredData.nodes.find(n => n.id === entityId)) {
            levels[entityId] = 2;
            visited.add(entityId);
          }
        });
        if (layer4Entities.length > 0) {
          layer4Entities.forEach(entityId => {
            if (filteredData.nodes.find(n => n.id === entityId)) {
              levels[entityId] = 3;
              visited.add(entityId);
            }
          });
          filteredData.nodes.forEach(node => {
            if (!visited.has(node.id)) {
              levels[node.id] = 4;
              visited.add(node.id);
            }
          });
        } else {
          filteredData.nodes.forEach(node => {
            if (!visited.has(node.id)) {
              levels[node.id] = 3;
              visited.add(node.id);
            }
          });
        }
        
        return levels;
      };
      
      const levels = getConnectionLevels();
      const nodesByLevel = {};
      filteredData.nodes.forEach(node => {
        const level = levels[node.id] || 0;
        if (!nodesByLevel[level]) nodesByLevel[level] = [];
        nodesByLevel[level].push(node);
      });

      let maxLevel = Math.max(...Object.keys(nodesByLevel).map(Number));
      const levelWidth = (width - 200) / (maxLevel + 1);
      
      Object.keys(nodesByLevel).forEach(level => {
        const levelNodes = nodesByLevel[level];
        const levelHeight = height - 100;
        const nodeSpacing = levelHeight / (levelNodes.length + 1);
        
        levelNodes.forEach((node, index) => {
          node.treeX = 100 + (parseInt(level) * levelWidth);
          node.treeY = 50 + ((index + 1) * nodeSpacing);
        });
      });
      
    } else {
      const linkDistance = 150;
      const chargeStrength = -400;
      
      simulation = d3.forceSimulation(filteredData.nodes)
        .force('link', d3.forceLink(filteredData.links).id(d => d.id).distance(linkDistance))
        .force('charge', d3.forceManyBody().strength(chargeStrength))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force('collision', d3.forceCollide().radius(35));
    }
    
    const container = svg.append('g');

    const zoom = d3.zoom()
      .scaleExtent([0.1, 4])
      .on('zoom', (event) => {
        container.attr('transform', event.transform);
      });
    
    svg.call(zoom);

    if (filterLevel === 'minimalCore' && layoutType === 'tree') {
      svg.append('defs').append('marker')
        .attr('id', 'arrowhead')
        .attr('viewBox', '0 -5 10 10')
        .attr('refX', 25.5)
        .attr('refY', 0)
        .attr('markerWidth', 3.5)
        .attr('markerHeight', 3.5)
        .attr('orient', 'auto')
        .append('path')
        .attr('d', 'M0,-5L10,0L0,5')
        .attr('fill', '#999');
    }

    let linksToShow = filteredData.links;
    let selfReferencingLinks = [];
    
    if (layoutType === 'tree' && filterLevel === 'minimalCore') {
      const rootNodeId = filteredData.nodes.find(n => n.id === 'ResearchStudy')?.id || filteredData.nodes[0]?.id;

      selfReferencingLinks = filteredData.links.filter(link => {
        const sourceId = link.source?.id || link.source;
        const targetId = link.target?.id || link.target;
        return sourceId === targetId;
      });

      linksToShow = filteredData.links.filter(link => {
        const sourceId = link.source?.id || link.source;
        const targetId = link.target?.id || link.target;

        if (sourceId === targetId) return false;
        if (sourceId === 'ResearchSubject' && targetId === rootNodeId) return true;
        if (targetId === rootNodeId) return false;
        
        return true;
      });
    }

    const link = container.append('g')
      .attr('class', 'links')
      .selectAll('line')
      .data(linksToShow)
      .enter().append('line')
      .attr('class', 'link')
      .attr('stroke', '#999')
      .attr('stroke-opacity', 0.6)
      .attr('stroke-width', 2)
      .attr('marker-end', (filterLevel === 'minimalCore' && layoutType === 'tree') ? 'url(#arrowhead)' : null);

    let loopPaths = null;
    if (layoutType === 'tree' && filterLevel === 'minimalCore' && selfReferencingLinks.length > 0) {
      loopPaths = container.append('g')
        .attr('class', 'loop-links')
        .selectAll('path')
        .data(selfReferencingLinks)
        .enter().append('path')
        .attr('class', 'loop-link')
        .attr('stroke', '#999')
        .attr('stroke-opacity', 0.6)
        .attr('stroke-width', 2)
        .attr('fill', 'none')
        // no arrow marker for self-loops
    }

    const node = container.append('g')
      .attr('class', 'nodes')
      .selectAll('g')
      .data(filteredData.nodes)
      .enter().append('g')
      .attr('class', 'node');

    if (layoutType !== 'tree') {
      node.call(d3.drag()
        .on('start', dragstarted)
        .on('drag', dragged)
        .on('end', dragended));
    }

    node.append('circle')
      .attr('r', 8)
      .attr('fill', '#4ecdc4')
      .attr('stroke', '#fff')
      .attr('stroke-width', 2);

    node.append('text')
      .attr('dx', 12)
      .attr('dy', 4)
      .style('font-size', '12px')
      .style('font-family', 'Arial, sans-serif')
      .text(d => d.id);

    node
      .on('mouseover', function(event, d) {
        tooltip.style('opacity', 1)
          .style('left', (event.pageX + 10) + 'px')
          .style('top', (event.pageY - 10) + 'px')
          .html(`<strong>${d.id}</strong><br/>
                 Connections: ${filteredData.links.filter(l => {
                   const sourceId = l.source?.id || l.source;
                   const targetId = l.target?.id || l.target;
                   return sourceId === d.id || targetId === d.id;
                 }).length}`);

        highlightConnections(d.id);
      })
      .on('mouseout', function() {
        tooltip.style('opacity', 0);
        resetHighlight();
      });

    if (layoutType === 'tree') {
      node.attr('transform', d => `translate(${d.treeX || 0},${d.treeY || 0})`);

      link
        .attr('x1', d => {
          const sourceNode = filteredData.nodes.find(n => n.id === (d.source.id || d.source));
          return sourceNode ? sourceNode.treeX || 0 : 0;
        })
        .attr('y1', d => {
          const sourceNode = filteredData.nodes.find(n => n.id === (d.source.id || d.source));
          return sourceNode ? sourceNode.treeY || 0 : 0;
        })
        .attr('x2', d => {
          const targetNode = filteredData.nodes.find(n => n.id === (d.target.id || d.target));
          return targetNode ? targetNode.treeX || 0 : 0;
        })
        .attr('y2', d => {
          const targetNode = filteredData.nodes.find(n => n.id === (d.target.id || d.target));
          return targetNode ? targetNode.treeY || 0 : 0;
        });

      if (loopPaths) {
        loopPaths.attr('d', d => {
          const nodeId = d.source?.id || d.source;
          const sourceNode = filteredData.nodes.find(n => n.id === nodeId);
          if (!sourceNode) return '';
          
          const x = sourceNode.treeX || 0;
          const y = sourceNode.treeY || 0;
          const radius = 20;
          
          return `M ${x + 8} ${y}
                  A ${radius} ${radius} 0 1 1 ${x + 8} ${y - 1}`;
        });
      }
      
    } else {
      simulation.on('tick', () => {
        link
          .attr('x1', d => d.source.x)
          .attr('y1', d => d.source.y)
          .attr('x2', d => d.target.x)
          .attr('y2', d => d.target.y);
        
        node
          .attr('transform', d => `translate(${d.x},${d.y})`);
      });
    }
    
    function dragstarted(event, d) {
      if (layoutType === 'force' && simulation) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
      }
    }
    
    function dragged(event, d) {
      if (layoutType === 'force') {
        d.fx = event.x;
        d.fy = event.y;
      } else {
        d.treeX = event.x;
        d.treeY = event.y;
        d3.select(event.sourceEvent.target.parentNode).attr('transform', `translate(${event.x},${event.y})`);
      }
    }
    
    function dragended(event, d) {
      if (layoutType === 'force' && simulation) {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
      }
    }
    
    function highlightConnections(nodeId) {
      const linksForHighlight = layoutType === 'tree' && filterLevel === 'minimalCore' ?
        [...linksToShow, ...selfReferencingLinks] : filteredData.links;

      node.style('opacity', d => {
        const isConnected = d.id === nodeId || 
          linksForHighlight.some(l => {
            const linkSourceId = l.source?.id || l.source;
            const linkTargetId = l.target?.id || l.target;
            return (linkSourceId === nodeId && linkTargetId === d.id) || 
                   (linkTargetId === nodeId && linkSourceId === d.id);
          });
        return isConnected ? 1 : 0.3;
      });
      
      link.style('opacity', d => {
        const sourceId = d.source?.id || d.source;
        const targetId = d.target?.id || d.target;
        return (sourceId === nodeId || targetId === nodeId) ? 1 : 0.1;
      });

      if (loopPaths) {
        loopPaths.style('opacity', d => {
          const sourceId = d.source?.id || d.source;
          return sourceId === nodeId ? 1 : 0.1;
        });
      }
    }
    
    function resetHighlight() {
      node.style('opacity', 1);
      link.style('opacity', 0.6);
      if (loopPaths) {
        loopPaths.style('opacity', 0.6);
      }
    }
    
  }, [filterLevel, layoutType, customLayers]);

  return (
    <div className="app">
      <div className="header">
        <h1>Schema Graph Visualization</h1>
        <p>Interactive graph showing relationships between schema entities</p>
        <div className="filter-controls">
          <div className="filter-section">
            <label htmlFor="filter-select">View: </label>
            <select 
              id="filter-select"
              value={filterLevel} 
              onChange={(e) => handleFilterChange(e.target.value)}
              className="filter-dropdown"
            >
              {Object.entries(filterLevels).map(([key, level]) => (
                <option key={key} value={key}>{level.name}</option>
              ))}
            </select>
            <span className="filter-description">{filterLevels[filterLevel].description}</span>
          </div>
          {filterLevel === 'minimalCore' && (
            <div className="layout-controls">
              <span className="layout-label">Layout: </span>
              <label className="radio-label">
                <input 
                  type="radio" 
                  value="force" 
                  checked={layoutType === 'force'} 
                  onChange={(e) => setLayoutType(e.target.value)}
                />
                Force
              </label>
              <label className="radio-label">
                <input 
                  type="radio" 
                  value="tree" 
                  checked={layoutType === 'tree'} 
                  onChange={(e) => setLayoutType(e.target.value)}
                />
                Tree
              </label>
            </div>
          )}
        </div>
      </div>
      <div className="graph-container">
        <svg ref={svgRef}></svg>
        <div ref={tooltipRef} className="tooltip"></div>
      </div>
      <div className="controls">
        {filterLevel === 'minimalCore' && layoutType === 'tree' && (
          <div className="layer-controls">
            <h4>Tree Layer Customization</h4>
            <div className="layer-input-section">
              <label htmlFor="layer2-input">Layer 2: </label>
              <input 
                id="layer2-input"
                type="text" 
                value={customLayers.layer2} 
                onChange={(e) => setCustomLayers({...customLayers, layer2: e.target.value})}
                placeholder="ResearchSubject"
                className="layer-input"
              />
            </div>
            <div className="layer-input-section">
              <label htmlFor="layer3-input">Layer 3: </label>
              <input 
                id="layer3-input"
                type="text" 
                value={customLayers.layer3} 
                onChange={(e) => setCustomLayers({...customLayers, layer3: e.target.value})}
                placeholder="Patient,Specimen,DocumentReference,MedicationAdministration,Observation"
                className="layer-input"
              />
            </div>
            <div className="layer-input-section">
              <label htmlFor="layer4-input">Layer 4: </label>
              <input 
                id="layer4-input"
                type="text" 
                value={customLayers.layer4} 
                onChange={(e) => setCustomLayers({...customLayers, layer4: e.target.value})}
                placeholder=""
                className="layer-input"
              />
            </div>
          </div>
        )}
      </div>
      <div className="footer">
      © 2025 CALYPR.
    </div>
    </div>
  );
};

export default App;