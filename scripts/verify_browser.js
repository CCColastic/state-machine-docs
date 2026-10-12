async (page) => {
  const currentUrl = page.url();
  if(!currentUrl.startsWith('file:'))throw Error('Open the standalone HTML file before verification');
  const base=currentUrl.split('#')[0].split('?')[0];
  await page.goto(base);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.waitForSelector('#diagram svg');
  const sections = await page.locator('#doc-data').evaluate(node => JSON.parse(node.textContent).sections);
  const results = [];
  for (const section of sections) {
    await page.goto(base + '?verify=' + section.id + '#' + section.id);
    await page.waitForSelector('#diagram svg');
    await page.waitForFunction(() => document.querySelector('#render-status').textContent.startsWith('Scroll to explore'));
    const grouped = await page.locator('#diagram svg').evaluate(svg => ({
      id: svg.id,
      nodes: [...svg.querySelectorAll('.node')].map(node => node.textContent).sort(),
      edges: svg.querySelectorAll('.flowchart-link').length,
      groups: svg.querySelectorAll('.cluster').length,
    }));
    await page.getByRole('button', { name: 'Flat', exact: true }).click();
    await page.waitForFunction(previous => document.querySelector('#diagram svg')?.id !== previous && document.querySelector('#render-status').textContent.startsWith('Scroll to explore'), grouped.id);
    const flat = await page.locator('#diagram svg').evaluate(svg => ({
      nodes: [...svg.querySelectorAll('.node')].map(node => node.textContent).sort(),
      edges: svg.querySelectorAll('.flowchart-link').length,
      groups: svg.querySelectorAll('.cluster').length,
    }));
    if (JSON.stringify(grouped.nodes) !== JSON.stringify(flat.nodes) || grouped.edges !== flat.edges || flat.groups !== 0) {
      throw Error('Diagram styles differ in nodes or edges: ' + section.id);
    }
    if (section.edges && flat.edges !== section.edges.length) throw Error('Extracted edge count differs: ' + section.id);
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
