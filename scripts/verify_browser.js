async (page) => {
  const currentUrl = page.url();
  if(!currentUrl.startsWith('file:'))throw Error('Open the standalone HTML file before verification');
  const base=currentUrl.split('#')[0].split('?')[0];
  await page.goto(base);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.waitForSelector('#doc-data', {state:'attached'});
  const sections = await page.locator('#doc-data').evaluate(node => JSON.parse(node.textContent).sections);
  const syntax = await page.evaluate(async sections => {
    if (!window.mermaid) return ['Diagram renderer unavailable'];
    const errors = [];
    for (const section of sections) for (const mode of ['mermaid', 'flat']) {
      try { await mermaid.parse(section[mode]); }
      catch (error) { errors.push(section.id + '/' + (mode === 'mermaid' ? 'grouped' : 'flat') + ': ' + error.message); }
    }
    return errors;
  }, sections);
  if (syntax.length) throw Error(syntax.join('\n'));
  const rendered = async (section, mode, previous) => {
    try {
      await page.waitForFunction(previous => {
        const status = document.querySelector('#render-status');
        return status.textContent.startsWith('Diagram could not render') ||
          (status.textContent.startsWith('Scroll to explore') && document.querySelector('#diagram svg')?.id !== previous);
      }, previous, {timeout:15000});
    } catch { throw Error('Rendering timed out: ' + section.id + '/' + mode); }
    const status = await page.locator('#render-status').textContent();
    if (status.startsWith('Diagram could not render')) throw Error(section.id + '/' + mode + ': ' + status);
    return await page.locator('#diagram svg').evaluate(svg => {
      const nodes = [...svg.querySelectorAll('.node')].map(node => node.dataset.id + '|' + node.textContent.trim()).sort();
      if (!nodes.length || svg.querySelector('.error-icon, .error-text')) throw Error('Expected a rendered flowchart, received an empty or error SVG');
      const labels = [...svg.querySelectorAll('.edgeLabels > .edgeLabel')];
      const transitions = [...svg.querySelectorAll('.flowchart-link')].map((path, index) =>
        [...path.classList].filter(name => name.startsWith('LS-') || name.startsWith('LE-')).sort().join('>') + '|' +
        (labels[index]?.getAttribute('aria-label') || labels[index]?.textContent.trim() || '')).sort();
      return {id:svg.id, nodes, transitions, edges:transitions.length, groups:svg.querySelectorAll('.cluster').length};
    });
  };
  const validateLoops = async section => {
    const loops=await page.locator('#diagram svg').evaluate(svg=>{
      const paths=[...svg.querySelectorAll('.flowchart-link')];
      const labels=[...svg.querySelectorAll('.edgeLabels > .edgeLabel')];
      return paths.flatMap((path,index)=>{
        const from=[...path.classList].find(name=>name.startsWith('LS-'))?.slice(3);
        const to=[...path.classList].find(name=>name.startsWith('LE-'))?.slice(3);
        if(!from || from!==to)return [];
        const arrow=path.getBoundingClientRect(),label=labels[index].getBoundingClientRect();
        return [{compact:path.dataset.compactLoop==='true',width:path.getBBox().width,gap:label.left-arrow.right,label:{left:label.left,right:label.right,top:label.top,bottom:label.bottom}}];
      });
    });
    if(loops.some(loop=>!loop.compact || loop.width<34 || loop.width>42 || loop.gap<4 || loop.gap>30))throw Error('Self-loop is oversized or its label is misplaced: '+section.id);
    for(let i=0;i<loops.length;i++)for(let j=i+1;j<loops.length;j++){
      const a=loops[i].label,b=loops[j].label;
      if(a.left<b.right && a.right>b.left && a.top<b.bottom && a.bottom>b.top)throw Error('Self-loop captions overlap; combine their events or split the view: '+section.id);
    }

  };
  const results = [];
  for (const section of sections) {
    await page.goto(base + '?verify=' + section.id + '#' + section.id);
    const grouped = await rendered(section, 'grouped');
    await validateLoops(section);
    await page.getByRole('button', { name: 'Flat', exact: true }).click();
    const flat = await rendered(section, 'flat', grouped.id);
    await validateLoops(section);
    if (JSON.stringify(grouped.nodes) !== JSON.stringify(flat.nodes) || JSON.stringify(grouped.transitions) !== JSON.stringify(flat.transitions) || flat.groups !== 0) {
      throw Error('Diagram styles differ in nodes or edges: ' + section.id);
    }
    if (section.edges && flat.edges !== section.edges.length) throw Error('Extracted edge count differs: ' + section.id);

    const before = await page.locator('#scale-label').innerText();
    await page.getByRole('button', { name: 'Zoom in', exact: true }).click();
    if (await page.locator('#scale-label').innerText() === before) throw Error('Zoom did not change');
    await page.getByRole('button', { name: 'Fit width', exact: true }).click();
    if(section.sources.length){
      await page.locator('#sources details').first().locator('summary').click();
      if (!await page.locator('#sources details').first().locator('pre').isVisible()) throw Error('Source evidence did not open');
    }
    results.push({ section: section.id, nodes: flat.nodes.length, edges: flat.edges });
  }
  if (await page.locator('#filter').count()) throw Error('Removed layer search is still present');
  await page.locator('#navigation a[href="#modules"]').click();
  await page.locator('#inventory').waitFor({state:'visible'});
  if (await page.locator("script[src]").count()) throw Error("Standalone HTML requires an external script");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.locator('#navigation a[href="#overview"]').click();
  await page.waitForSelector('#diagram svg');
  if (await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth)) throw Error('Mobile page overflows');
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto(base + '#overview');
  await page.waitForSelector('#diagram svg');
  return { verified: results, mobile: 'passed', sourceExcerpts: 'passed', offline: true, layerSearch: 'removed' };
}
