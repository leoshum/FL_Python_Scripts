import { ComponentFixture, TestBed } from '@angular/core/testing';

import { TeamCityVersionComponent } from './team-city-version.component';

describe('TeamCityVersionComponent', () => {
  let component: TeamCityVersionComponent;
  let fixture: ComponentFixture<TeamCityVersionComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ TeamCityVersionComponent ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(TeamCityVersionComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
