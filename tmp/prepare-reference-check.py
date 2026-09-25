from pathlib import Path
s=Path('tmp/check-design-skill.cjs').read_text()
s=s.replace("skillName:'koi-menu-pdf',designPrompt", "skillName:'koi-menu-pdf',reference:{name:'reference.pdf'},designPrompt")
s=s.replace("  if(p.endsWith('/design-skill')){", "  if(p.endsWith('/reference'))return route.fulfill({path:'Kemang Lunch & Dinner 20260605A.pdf',contentType:'application/pdf',headers:{'Content-Disposition':'attachment; filename=reference.pdf'}});\n  if(p.endsWith('/design-skill')){")
s=s.replace("  assert.equal(await page.locator('.skill-context strong').innerText(),r.name);", """  assert.equal(await page.locator('.skill-context strong').innerText(),r.name);
  const view=page.getByRole('link',{name:'View reference PDF'});assert.equal(await view.getAttribute('href'),'/api/ai/restaurants/'+r.id+'/reference');assert.equal(await view.getAttribute('target'),'_blank');
  const pdfDownload=page.waitForEvent('download');await page.getByRole('link',{name:'Download reference PDF'}).click();assert.equal((await pdfDownload).suggestedFilename(),'reference.pdf');""")
s=s.replace('tmp/design-skill-', 'tmp/reference-viewer-')
Path('tmp/check-reference-viewer.cjs').write_text(s)
