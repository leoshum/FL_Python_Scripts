import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { WebsiteLoadTimeComponent } from './website-load-time/website-load-time.component';
import { TeamCityVersionComponent } from './team-city-version/team-city-version.component';
import { TeamCityCommentComponent } from './team-city-comment/team-city-comment.component';

const routes: Routes = [
  { path: 'websiteloadtime', component: WebsiteLoadTimeComponent },
  { path: '', component: WebsiteLoadTimeComponent },
  { path: 'teamcitycomment', component: TeamCityCommentComponent },
  { path: 'teamcityversions', component: TeamCityVersionComponent }
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }
