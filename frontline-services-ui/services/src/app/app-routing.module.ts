import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { WebsiteLoadTimeComponent } from './website-load-time/website-load-time.component';
import { TeamCityVersionComponent } from './team-city-version/team-city-version.component';

const routes: Routes = [
  // { path: '', component: HomeComponent },
  { path: 'websiteloadtime', component: WebsiteLoadTimeComponent },
  { path: 'teamcityversions', component: TeamCityVersionComponent }
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }
