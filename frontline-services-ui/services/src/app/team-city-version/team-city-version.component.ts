import { HttpClient } from '@angular/common/http';
import { Component } from '@angular/core';
import { API_URL } from '../constants';

@Component({
  selector: 'app-team-city-version',
  templateUrl: './team-city-version.component.html',
  styleUrls: ['./team-city-version.component.scss']
})
export class TeamCityVersionComponent {
  constructor(private http: HttpClient) {}

  isRequesting = false;
  isCollapsed = true;
  isHideEmptyEnvironments = true;
  configuration: any;
  
  ngOnInit() {
    const url = API_URL + 'version_configuration';
    this.http.get(url).subscribe(
      (response: any) => {
        this.configuration = response.map((environment: any) => {
          return {
            Environment: environment.Environment,
            Clients: environment.Clients,
            Collapse: true
          };
        });
      },
      error => {
        console.error(error);
      }
    );
  }

  collapse_all(){
    let all_wrong = true;
    this.configuration.forEach((environment: any) => {
      if (environment.Clients.length > 0 || !this.isHideEmptyEnvironments){
        if (all_wrong && environment.Collapse == this.isCollapsed) {
          all_wrong = false;
        }
      }
    });
    this.configuration.forEach((environment: any) => {
      if (all_wrong) {
        this.isCollapsed = this.isCollapsed;
      } else {
        environment.Collapse = !this.isCollapsed;
      }
    });
  }

  collapse(environment:any){
    environment.Collapse = !environment.Collapse;
  }
}
