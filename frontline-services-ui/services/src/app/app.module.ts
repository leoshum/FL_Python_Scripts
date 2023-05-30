import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { FormsModule } from '@angular/forms';
import { HttpClientModule } from '@angular/common/http';

import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';
import { NavbarComponent } from './navbar/navbar.component';
import { WebsiteLoadTimeComponent } from './website-load-time/website-load-time.component';
import { TeamCityVersionComponent } from './team-city-version/team-city-version.component';
import { TeamCityCommentComponent } from './team-city-comment/team-city-comment.component';

@NgModule({
  declarations: [
    AppComponent,
    NavbarComponent,
    WebsiteLoadTimeComponent,
    TeamCityVersionComponent,
    TeamCityCommentComponent
  ],
  imports: [
    BrowserModule,
    AppRoutingModule,
    FormsModule,
    HttpClientModule
  ],
  providers: [],
  bootstrap: [AppComponent]
})
export class AppModule { }
